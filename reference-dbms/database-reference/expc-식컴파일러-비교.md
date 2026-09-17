# database-reference 비교 — 레지스터 머신형 식 컴파일러(`expc`) 대 CUBRID `expr_compile` (2026-09-16)

> 작성: 정소희 (.52) · 원 위치 `claude-workspace/projects/CBRD-27215/` → 2026-09-17 이 리포로 이관(문서지도: 소스·참조 DBMS 분석은 dev4-ai-source). 프로젝트 문맥은 `claude-workspace/projects/CBRD-27215/설계문서-발표.md` D27·D28·NUMERIC 절.

- 대상: **database-reference**(`~/dev/database-reference/src/include/server/module/{executor/expc,expression_eval,pp}`, 헤더만 있음 — 명령 해석 루프·레지스터 회수 본체·컬럼/파라미터/집계 컴파일 특수화의 `.cc`는 없어서 그 부분은 호출 지점에서 추론) 대 `feature/expression-compile`의 `src/query/expr_compile.c` (`68909640f`).
- 원칙: database-reference의 코드를 옮기지 않는다. **설계 아이디어만** 읽고 CUBRID 구조에 맞게 새로 쓴다. 출처 표기는 "database-reference 참고"로 한다.
- 결론: 두 가지를 가져왔다(D27 합성 호이스팅, D28 n항 AND/OR 체인). 다섯 가지는 이유를 적고 가져오지 않았다. 세 가지는 우리가 이미 앞서 있다.

## 1. 대응표

| 축 | database-reference (expc) | CUBRID expr_compile (이 PR) |
|---|---|---|
| 형태 | 레지스터 머신 바이트코드. `Instruction{op, src_pos, args[6]}`, 값 레지스터 + **3치 불리언 레지스터** + 상수 레지스터 + 컬럼 레지스터 | 평평한 스텝 배열. 셀(포인터)/슬롯(값) 분리, 커널 함수 포인터, 점프 스텝 |
| 컴파일 시점 | 플랜 생성 시(`compile_and_meta_eval`: 타입·자릿수 해석과 코드 생성이 한 패스) | 서버, 클론 첫 실행 첫 행(바인드 타입 확정 후). `DB_TYPE_VARIABLE`은 한 행 미룬다(D26) |
| 프로그램 수명 | **공유 메모리 플랜 캐시(Pp)에 저장**, 노드마다 `expc_node_index`. 레지스터 파일만 실행마다 노드가 가짐(`NodeRegisters`) | 클론과 함께 산다(D21). 실행 끝에 슬롯 값만 비움, 바인드 타입 서명 대조 후 재사용/재컴파일 |
| 실행 단위 | 실행 노드당 여러 expc가 **레지스터 파일 하나를 공유** | 리스트당 프로그램 하나(출력·집계 인자·스캔 필터). 필터→소비자 공유는 별도 장치(D19) |
| 한 번만 계산 | **레지스터 격자**: 상수가 씨앗, 이항 연산은 두 입력이 모두 once-eval이면 결과도 once-eval. `OnceEvalProhibitStart/End`로 분기 안 저장 금지 | (전) 리터럴·호스트 변수 읽기와 그 coerce만 P/E 프롤로그. (후, D27) 입력 셀의 고정 등급을 합성해 산술·cast·extract도 호이스팅 |
| 레지스터/슬롯 | 소비 즉시 `VacateRegister`로 **회수·재사용**, 컴파일 인덱스와 실행 번호 두 층 | 계산 스텝마다 64B 슬롯 하나, 회수 없음 |
| 공통 부분식 | `share_number`를 옵티마이저가 매김. 컴파일러의 노드 간 공유는 **TODO** | 값 번호 매기기 CSE + 교환법칙(D22) + 값 같은 리터럴 + 가드별 공유(D14) + 필터→소비자(D19) |
| AND/OR | **n항**, 공유 불리언 레지스터 하나 + 조건 점프, 모든 탈출을 한 지점으로 되메움 | (전) 이항 트리 재귀. (후, D28) 스캔 필터에서 같은 연결자의 체인을 한 노드로 평탄화 |
| 조건부 평가 | CASE/DECODE: `kConditionNotTrueJump`(FALSE·UNKNOWN 모두 다음 WHEN), 분기마다 스크래치 레지스터 회수, 결과 캐스트를 ELSE 뒤 트레일러로 | 점프 스텝(`jump_null`·`jump_notnull`·`case_branch`·`jump`), 한 방향 실행(D20) |
| COALESCE | 모든 인자 평가 후 UDI 하나(단락 없음) | NVL/COALESCE 점프로 건너뜀 |
| 타입 결정 | 결과 메타를 컴파일 시점 표(`DB_OPD_COMB`, 정밀도 최대치)로 확정, 명령에 (from,to) 캐스트를 실어 보냄 | 실제 바인드 값/컬럼 도메인으로 커널을 고름. 해석 경로와 **byte 동일**이 기준 |
| 폴백 | `kUdi`(서브쿼리·UDF·포맷 캐스트·COALESCE·그룹 비교) | `expr_k_fallback`(부분 트리 해석), 커버 못 한 컬럼은 예전 경로 |
| 오류 위치 | 명령마다 `SrcPos` | 없음(XASL에 소스 위치가 없다) |
| 덤프 | `Expc::Dump()` | `;trace on`의 EXPR_COMPILE 절 |
| 인덱스 키 | `IndexKeyEvaluator`가 컴파일 경로 | 미적용(스캔 필터·출력·집계 인자만) |

## 2. 가져온 것

### D27 합성 호이스팅 (once-eval 격자)

- **무엇**: 셀마다 "값이 얼마나 자주 바뀌나"를 기록한다 — 리터럴은 절대 안 바뀜, 호스트 변수는 실행 사이에만, 나머지는 행마다. 계산 스텝의 등급은 입력 셀 등급의 합성이다. 두 입력이 모두 고정이면 그 스텝도 고정이고, 리터럴만으로 만들어졌으면 P 프롤로그, 호스트 변수가 끼면 E 프롤로그로 간다.
- **왜**: `? * 2`, `1 - 0.05`, `cast(? as int)`, `extract(year from ?)`가 지금까지 행마다 다시 계산됐다. 잎만 끌어올리고 그 위는 두던 것을, database-reference처럼 도출 규칙으로 바꾸면 손으로 표시할 곳이 없어진다.
- **어디까지**: 실패할 수 있는 스텝(산술·cast)은 **메인 루프에서만** 끌어올린다. 가드 영역(해석 경로가 건너뛸 수 있는 오른쪽)에서 끌어올리면 없던 오류를 낼 수 있다 — `a + 1/?`에서 a가 NULL이면 해석 경로는 `1/?`를 계산하지 않는다. 실패하지 않는 스텝(coerce·extract)은 이전처럼 분기 밖이면 어디서든. CASE 분기 안은 어느 쪽도 안 한다(분기는 점프가 건너뛰는 연속 구간). lazy 노드(NULL 검사 점프가 자기 슬롯에 별칭된 것)는 그대로 행 루프에 둔다.
- **database-reference와 다른 점**: 그쪽은 `OnceEvalProhibitStart/End`로 "공유 결과 레지스터에 쓰는 Move"만 금지하고, 실패 가능성은 보지 않는다(오류 시점이 바뀌어도 되는 시맨틱). 우리는 오류가 나는 행까지 해석 경로와 같아야 하므로 가드 조건을 추가했다.
- **코드**: `EXPR_BUILD_CTX.cell_fixed[]`, `expr_cells_fixed_class()`, `expr_step_hoist()`. 산술·cast·extract·coerce 발행 지점 5곳에서 부른다. `expr_prog_finish`의 P/E/행 안정 분할과 `expr_prog_enter_execution`은 그대로다.

### D28 스캔 필터의 n항 AND/OR 체인

- **무엇**: 같은 연결자로 이어진 체인을 한 노드(`kids[]`)로 평탄화하고 행마다 루프 하나로 평가한다. FALSE(OR는 TRUE)와 ERROR에서 즉시 나가고, UNKNOWN을 만나면 결과를 UNKNOWN으로 낮춘다.
- **왜 같은 답인가**: 해석 경로는 `(a AND b) AND c`도 `a AND (b AND c)`도 a, b, c 순서로 평가하고 같은 지점에서 멈춘다. 평탄화는 그 순서를 왼쪽부터 DFS로 모은 것이라 단락 지점·오류 발생 지점·3치 결과가 같다. 통과한 행이 AND 체인의 모든 피연산자를 평가했다는 사실도 그대로라 필터→소비자 공유 레지스트리에 영향이 없다.
- **비용**: 행마다 깊이만큼 재귀 호출과 kind 스위치를 하던 것이 피연산자 수만큼의 루프 반복으로 바뀐다. 5항 필터면 호출 4번이 준다. 크지 않지만 스캔 필터는 행당 핫패스다.
- **database-reference와 다른 점**: 그쪽은 공유 불리언 레지스터 하나에 `SetBoolFrom` 뒤 `kConditionNotTrueJump`로 탈출하는 바이트코드다. 이름대로면 `UNKNOWN AND FALSE`가 UNKNOWN이 되어 SQL과 어긋날 수 있다(해석 루프가 없어 확정은 못 함). 우리는 결과 누적 변수를 두어 Kleene 규칙을 그대로 지킨다.
- **코드**: `EXPR_PRED_AND_N/OR_N`, `kids/n_kids`, `expr_scan_pred_chain_collect()`, `expr_scan_pred_build_chain()`, `expr_pred_eval_chain()`. free·materialize·leaf 카운트·dump가 kids를 걷는다. 128항을 넘으면 트리 전체를 해석 경로에 둔다(깊이 제한과 같은 정책). T_PREDICATE 값 술어 빌더는 이항 그대로다.

## 3. 가져오지 않은 것과 이유

- **레지스터 회수·두 층 번호 매기기.** 우리 슬롯은 리스트당 보통 10개 미만(Q1은 4개)이라 이득이 미미하고, 슬롯이 프라이빗 힙 문자열을 가질 수 있어 재사용 전 정리 규칙이 필요하며, 여러 루트에 걸친 CSE 히트가 있어 소비 시점에 회수하려면 전체 루트 컴파일 후 생존 구간 분석이 필요하다. database-reference가 CSE를 TODO로 둔 이유가 바로 이 충돌이다. 우리는 CSE를 택했다.
- **명령별 SrcPos.** XASL/regu에 소스 위치가 없다. 클라이언트 파서가 위치를 버린 뒤라 서버에서 복원할 수 없다.
- **3치 불리언 레지스터 파일.** 우리 술어 트리는 `DB_LOGICAL`을 반환하는 노드 평가로 충분하고, 값 프로그램의 비교(T_PREDICATE)는 INTEGER/NULL을 만든다. 별도 레지스터 파일이 줄 이득이 없다.
- **노드 단위 공유 레지스터.** 힙 컬럼은 스캔이 값 리스트에 행마다 한 번 디코드하므로 컬럼 공유는 이미 자연히 된다. 식 결과 공유는 D19(필터→소비자)가 실제 필요한 경우를 덮는다.
- **컴파일 시 메타 확정(타입 표).** 우리 기준은 해석 경로와 byte 동일이고, 도메인은 실제 값에서 나온다. 표로 미리 정하면 `tp_domain_resolve_value`와 어긋날 위험을 진다. D26의 한 행 미루기가 정확성을 구조적으로 보장한다.
- **UDI.** `expr_k_fallback`이 같은 역할이다.

## 4. 우리가 이미 앞선 것

- 공통 부분식 공유(값 번호 매기기·교환·값 같은 리터럴·가드별·필터→소비자). 그쪽은 `is_shared_reg` 배관만 있고 정책이 TODO다.
- COALESCE/NVL의 단락. 그쪽은 인자를 전부 평가한다.
- 회귀 시험이 규칙마다 붙어 있고, "해석 경로와 byte 동일"이 검증 기준이다.

## 5. database-reference 코드에서 눈에 띈 결함 (헤더 기준, 확정은 아님)

- `RegisterGenContext::set_once_eval`이 `is_once_eval_ && once_eval_prohibited`로 AND — 이름대로면 반전이다.
- `MetaEvalOperatorIsNotNull`이 빈 함수인데 디스패치 표에 걸려 있다. 상위 재작성에 기대는 구조.
- AND/OR가 "마지막 값이 남는" 방식이라 `UNKNOWN AND FALSE`, `UNKNOWN OR FALSE`가 SQL과 다를 수 있다.
- `_MetaEvalOperatorSubResult`의 `DOUBLE_X_DOUBLE → SetBinaryFloat()` (다른 셋은 `SetBinaryDouble()`).
- n항 `-`·`/`를 오른쪽 결합으로 접는다.
- `__EXPR_GEN_TYPE_INIT(n)`이 `reg_idx`를 `{kExpcRegisterNull,}`로 초기화해 1번 이후 원소가 0(유효 레지스터)이 된다 — 선택 인자를 명시하지 않은 핸들러가 레지스터 0을 넘긴다.
- `MetaEvalFunctionChr`의 `result` 미초기화 역참조, `MetaEvalFunctionCoalesce`의 `res_type` 미초기화 읽기, `MetaEvalFunctionInitcap`의 `int len[0]`, `MetaEvalFunctionLRPad` 끝의 `to_type[2]` 덮어쓰기, `MetaEvalFunctionNvl2`의 arg[1] 이중 MetaCast, `instr_func_idx_tab`의 CLOB/NCLOB 짝 뒤바뀜.
- LIKE 패턴 분석 경로가 `false &&`로 꺼져 있고 술어가 미구현. REGEXP 전부 미구현.

## 6. 숫자형·값 표현 비교 (database-reference `common/datatype`, `server/module/datatype` 대 CUBRID `DB_VALUE`/`DB_NUMERIC`)

| 축 | database-reference | CUBRID |
|---|---|---|
| NUMBER 표현 | 밑 100 packed 10진, 빅엔디언 자릿수, 부호 의존 보수 인코딩(양수 0x80+d, 음수 0x80−d), 7비트 편향 지수(부호별 편향), **가변 길이**(size 바이트, 최대 22바이트), 최대 38자리. 정밀도·스케일은 값에 없고 메타(16바이트, 별도 객체)에만 | 밑 256 **2진 크기(부호 없음)** 17바이트, 부호는 헤더 플래그 `is_value_negative`, 정밀도·스케일은 값 헤더에, 최대 40자리. 디스크도 헤더 3바이트(크기·부호 비트·정밀도·스케일) + 가변 크기 |
| NULL | 길이 0 | 헤더 플래그 |
| 비교 | size 바이트 뒤부터 **memcmp**, 길이로 판정, 음수는 꼬리 센티널. 스케일 맞추기 없음(지수형) | 스케일 정렬 → 부호 플래그 → 크기 비교. memcmp 불가 |
| 산술 | 제자리·메타 인자 없음. 자릿수 배열로 풀어 밑 100 올림. 결과 자릿수는 실제 자릿수에서 | 64비트 워드 3개(`NUMERIC_AS_WORDS`)로 ALU 연산. 결과 정밀도·스케일은 피연산자 규칙 + 플랜 도메인 강제 |
| 집계 | 지수 위치별 int64 128칸(1KB) 누산기(`NumberAgg`) | 27178 `SUM_ACC` 3워드 상주 누산기, 그룹당 1회 팩 |
| 값 객체 | 120바이트, **타입 없음**(ptr + flags + size + 100바이트 인라인 아레나). 소유는 NEED_FREE 비트. 복사 금지(명시적 clone) | 64바이트 = 캐시라인 1개, 자기 서술(타입·정밀도·스케일·콜레이션), `need_clear` |
| 정수·실수 | `BIN_INT32/64`, `BINARY_FLOAT/DOUBLE`이 SQL 가시 타입. 정수는 빅엔디언 저장 | INTEGER/BIGINT/DOUBLE 그대로 |

**판정.**
- **실행기 관점에서는 CUBRID 표현이 낫다.** 2진 워드 표현은 더하기·곱하기가 CPU 정수 연산 그대로다. database-reference는 10진이라 산술마다 디코드→올림→인코드가 들고, SUM만을 위한 1KB 누산기를 따로 둔다. 우리 슬롯이 캐시라인 하나라는 것도 컴파일된 레지스터 파일에 큰 장점이다(그쪽 값은 라인 둘).
- **저장·인덱스 비교 관점에서는 database-reference가 낫다.** 키를 디코드 없이 memcmp로 정렬하고 작은 수를 짧게 저장한다.
- **안전성은 CUBRID.** 값이 타입을 들고 다녀 오해석 여지가 없고, 컴파일러의 행당 타입 가드도 그 덕에 가능하다. 그쪽은 값과 메타를 관례로만 짝지운다.
- **바꿀 만한 한 가지**: 부호를 크기 버퍼 밖 플래그로 두는 방식이 09-11 리터럴 공유 결함의 원인이었다. 부호가 바이트 안에 있는 표현(2의 보수 17바이트, 디스크 형식은 그대로 두고 읽기·쓰기에서 변환)이면 그 종류의 실수가 구조적으로 불가능하다. 발표자료 마지막 세 장(NUMERIC 표현 ①②③)에 A 현행 / B 부호 내장 2진 / C 순서 보존 10진의 장단점·연산 경로·예시 코드를 놓고 **B를 후속 PR로** 권고했다.

**database-reference 값·숫자 코드에서 눈에 띈 것(헤더 기준).** `Value(const Number&)` 생성자와 `ValueFrom(const Number&)`가 `size_`의 뜻(size 바이트 포함 여부)에서 1 어긋남 · `GetData<Number>()`의 인라인 경로가 `data_[size_]`를 쓸 때 `size_ == 100`이면 범위 밖 · `Serialize(void*)`가 아웃라인 페이로드를 무시 · Boost load 경로가 `new char[]`로 할당하고 `NEED_FREE`를 세우지 않음 · `DBMeta::kind`가 복사 생성자와 `==`에서 빠짐 · `SetWithType`에 `BIN_UINT64` 케이스 없음 · `number_get_exp` 주석의 zero 지수(−62)가 현재 편향 상수(−65)와 어긋남 · `NUMBER_NULLVAL_SUPPORTED`·`NUMBER_EXTVAL_SUPPORTED`가 꺼져 있어 ±inf·±0이 만들어지되 산술에서 전파되지 않음.

## 7. 실행 시점 비교 — database-reference `executor/` 헤더 대 CUBRID 행 경로 (2026-09-16)

전제: database-reference에는 실행기의 `.cc`가 없다(`ExecutorNodeBase` 정의·`Expc::Evaluate` 루프·노드 구현 전부 부재). 아래는 헤더 선언과 주석에서 읽은 데이터 모델 비교다. 풀/푸시 여부, 명령 디스패치 방식, 레지스터 초기화 시점은 판정 불가.

| 축 | database-reference (선언 기준) | CUBRID (이 PR 시점) |
|---|---|---|
| 노드 사이 단위 | **블록 단위**. `Table` = 블록 핸들의 침입형 리스트(버퍼 페이지 `TableBlockHandle` 또는 사설 2KB 청크 `ChunkHandle`). 건네주기는 O(1) 포인터 이어붙이기(`Splice`/`Move`) | **행 단위**. `scan_next_scan` → 필터 → 출력 → 필요하면 리스트 파일에 튜플 복사. 정렬·그룹 지점마다 리스트 파일로 물질화 |
| 행의 자리 | `RowPiece`가 청크 바이트 위에 그대로 얹힌 헤더(`flags|colcnt|length|offsets[]|data`). `RowPos = {블록, 행번호}`가 해시 가능한 행 참조 → 조인·그룹이 행을 복사 없이 가리킨다 | 값 리스트 `DB_VALUE[]`(디코드 복사) → 튜플 페이지에 다시 패킹 → 소비자는 `TYPE_POSITION`으로 튜플 바이트를 다시 언팩 |
| 컬럼 접근 | 식 그룹별 사용 컬럼 마스크(`out/where/key/all`), `ColumnBuilder`가 **`Value`를 블록 메모리로 포인팅**(복사 없음), `Skip()`으로 디코드 생략 | 술어 컬럼/나머지 컬럼 두 묶음(`pred_attrs`/`rest_attrs`)만 디코드. 이 PR의 `rd_readval` 커널이 디코드를 타입 고정으로 만들었지만 여전히 `DB_VALUE`로 **복사** |
| 필터 | 블록 안에서 **무효화 표시**(`InvalidateRowsByFilter(bool*, …, rowcnt)`) 뒤 `Compact`. 선택 벡터 모양 | 행마다 판정, 통과한 행만 다음 단계로(복사 없이 흘러가나 블록 개념 없음) |
| 식 평가 | 행 단위 스칼라 `Evaluate(ctx)` — 벡터 오버로드 없음. 노드당 레지스터 파일을 행마다 재사용. `child_cols_`가 자식별 배열이라 조인 양쪽을 한 명령 열에서 다룸 | 리스트당 프로그램, 슬롯을 행마다 재사용. 조인 조건은 미컴파일 |
| 집계 상태 | `ExAggr = uchar_t*` 바이트 덩어리, 오프셋 0에 count(Add·Subtract → 윈도 되감기). 해시 GROUP BY 상태를 **키와 같은 청크 행에** 기록 | 해시 엔트리가 별도 누산기 배열을 가리킴. SUM_ACC 3워드 상주 |
| 결과 전달 | 결과 집합이 곧 `Table`(청크 리스트). 클라이언트가 **청크 수**로 fetch. 원격 블록은 복사 없이 청크로 감쌈 | 리스트 파일 튜플을 행 수 단위로 전송 |
| 메모리 | 워커별 아레나 + `MemoryTuner` 피드백, 블록 `Clone`으로 아레나 이동, 4MB−24 리전(버디 8MB 반올림 회피) | 프라이빗 힙 + 워크스페이스, 슬롯 64B 정렬 |
| 벡터화 | 없음(SIMD·정렬·힌트 전무) | 없음 |

> **정정(09-16, [참조설계-비교-실행계층.md](실행계층-데이터계층-분리-분석.md) §3).** 아래 "복사가 세 번"은 틀렸다. CUBRID 힙 스캔은 기본 PEEK(`scan_id->fixed`)이고 `data_readval(copy=false)`로 DB_VALUE가 레코드 안을 가리키며, 리스트 스캔의 `TYPE_POSITION`도 peek다. 행당 강제 복사는 리스트 파일 패킹 1회이고, 차이는 복사 횟수가 아니라 **패킹 결과가 임시 파일 페이지에 사느냐(우리) 사설 청크에 사느냐(저쪽)**다. 실행 계층 전체 비교는 그 문서가 정본이다.

**판정.** "깔끔하다"는 인상은 맞지만 이유는 **아키텍처**다 — 노드 사이 통화가 블록 하나로 통일되어 있고 값이 블록 메모리를 가리켜 행당 복사가 거의 없다. CUBRID는 값 리스트·리스트 파일·튜플 디스크립터가 섞인 행 단위 경로라 복사가 세 번(디코드, 튜플 패킹, 소비자 언팩) 든다. 이것은 PR 규모의 변경이 아니라 실행기 재설계다. 이 PR이 건드린 층(식 평가·집계 인자·필터)에서는 두 쪽이 같은 모양(스칼라 행 평가 + 노드/리스트 단위 레지스터 재사용)이다.

**가져올 만한 한정된 것.** ① 해시 GROUP BY 상태를 키 옆에 두는 배치(엔트리 → 별도 누산기 포인터 추적 제거). ② 소비자별 사용 컬럼 마스크(지금은 술어/나머지 두 묶음). ③ 힙 레코드의 가변 길이 컬럼을 복사 대신 포인팅(peek)으로 두는 범위 확대 — 값 수명이 스캔 캐시에 묶이는 조건을 확인해야 한다. 셋 다 이 PR 밖.
