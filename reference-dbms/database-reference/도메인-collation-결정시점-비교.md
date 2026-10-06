# database-reference 비교 — 값 없는 자리의 도메인·collation 을 **언제, 어디서** 정하는가 (2026-10-06, .52)

대상: CUBRID PR#8022(CBRD-27510, head `cb0514bb7`) "도메인·collation 을 실행 전에 고정" 대 database-reference 참고의 식 컴파일 패스.
database-reference 쪽은 **헤더 중심 트리**(실행기 `.cc` 부재)라 아래 "참고" 열의 사실은 전부 헤더·컴파일러 `.cc` 기준이며, 실행 시점 동작은 추정하지 않았다.
표기 규약: 제품명을 쓰지 않고 "database-reference 참고"로만 적는다.

## 0. 한 장 요약

| 축 | database-reference 참고 | CUBRID develop(PR 전) | CUBRID PR#8022 |
|---|---|---|---|
| 결정 시점 | **컴파일 한 패스**(`compile_and_meta_eval`): 타입·자릿수 해석과 코드 생성이 같이 끝난다 | **행에서**: fetch 의 VARIABLE 확정, 비교 coerce, 집계 첫 값 … 43곳 | **실행 직전 1회**(`qexec_resolve_domains`, `qexec_execute_mainblock` 앞) + 로드 1회(`stx_build_domain_plan`) |
| 값 없는 자리(바인드)의 출발 타입 | `ExpnBindParameter` → `set_meta(DBType::UNKNOWN)` | `DB_TYPE_VARIABLE`(`tp_Variable_domain`) | 같음 — 컴파일은 develop 과 같은 도메인을 쓰고 GATE 슬롯만 표시 |
| UNKNOWN 이 섞인 연산 | **전파**: 한쪽이 UNKNOWN 이면 결과도 `SetUnknown()`; 함수 인자 검사는 UNKNOWN 이면 건너뜀 | 행에서 값의 타입으로 | 게이트가 바인드 값 타입으로 한 번에 확정, 플랜 항목(`DOMAIN_PLAN_ITEM`)에 pre-cast |
| 피연산자 조합 → 결과 메타 | 정적 표 `DB_OPD_COMB_TYPE`(NUMBER×NUMBER, NUMBER×DATE, …) → `GetPlusDBMeta(comb)` 등, 정밀도는 **최대치** | `tp_domain_resolve_value` 로 값에서 | `domain_rules.c` 타입 규칙 + 정적 변환 표(ASSIGN/IMPLICIT/COMPARE/OPERAND 모드) |
| 캐스트가 놓이는 곳 | 명령 스트림에 `AppendInstructionCast(from,to)`; 암묵 허용은 `IsConvertibleType(from,to)` 표 | 행마다 `tp_value_coerce` | 플랜 항목의 변환기(`conv[]`)·게이트가 고른 변환 셀 |
| 표현식 단위 collation | **없다** — 파서에 `COLLATE` 미지원 TODO, 정렬은 NLS(`nls_sort.cc`) 전역 | 행이 고르는 가지(ELT) 의 collation 을 따름 | 가지 collation 을 `LANG_RT_COMMON_COLL`(코드셋 공통 collation)로 **병합**, 병합 불가면 행에서 -1150 |
| 집합연산 열 타입 | `LpNodeSet.setcol_` 에 열 식 목록만; 통일 규칙은 트리에서 **확인 불가**(미구현 주석) | 양쪽 다 행 있을 때만 -456 | 한쪽이 비어도 실행 전 -456 |
| MEDIAN / PERCENTILE | `MEDIAN == PERCENTILE_CONT_AN`(같은 기본함수, `expn_fn_aggr_util.h:36`); 인자 타입 규칙은 헤더에서 **확인 불가** | 첫 값으로 DOUBLE→DATETIME→TIME 시도 | DOUBLE 고정(날짜 문자열 -1118) |
| 세션변수 | 서버 트리에 **해당 없음** | 행마다 값 타입 | 문장 동안 한 타입, 다른 타입 대입은 실행 전 -1384 |
| 결정 비용 | **플랜당 1회**(공유 플랜 캐시 `Pp` 에 저장) | 행마다 | **실행당 1회** + `RESOLVED_DOMAIN` 블록 할당 |

**결론.** 두 쪽 다 "행에서 타입을 정하지 않는다"로 수렴한다. 갈리는 축은 **딱 하나 — 결정 시점**이다. database-reference 참고는
컴파일에서 끝내고(바인드는 UNKNOWN 전파), CUBRID PR 은 실행 직전에 한다. 이 차이는 결함이 아니라 전제의 차이다:
CUBRID 는 prepare 가 바인드 타입을 싣지 않고, 캐시된 XASL 클론 하나가 서로 다른 바인드 타입의 실행을 받으며, 캐시 키에 타입이 없다.
그 전제에서는 컴파일 시점 핀이 불가능하고, 실행당 1회가 최선이다. **그 근거가 코드에 적혀 있지 않다**는 것이 PR 에 대한 유일한 설계 지적이다(D1-01).

## 1. 결정 시점 — 컴파일 vs 실행 직전

- database-reference 참고: `include/server/module/expression_eval/compile_and_meta_eval/` 10개 헤더. `MetaEvalFunction*`/`_MetaEvalOperator*` 가
  피연산자 메타를 읽어 결과 `dbmeta()` 를 세우고 같은 자리에서 `AppendInstructionCast(gen_ctx, src_pos, reg, from, to)` 로 캐스트 명령을 생성한다
  (`compile_and_meta_eval_function_impl.h:2644` "explicit casting 이 불가능한 경우 implicit casting 을 한다" — `datatype::IsConvertibleType` 로 판정).
  SQL 처리기 API 순서는 `Prepare → SqlCompile → Open(바인드) → BindParameter → GenerateExecutorCm → Execute`(`sql_processor.h:71-80`) —
  바인드 **뒤에** 실행용 산출물(`ExecutorCm`)을 만드는 단계가 있다. 그 안에서 UNKNOWN 을 다시 해석하는지는 `.cc` 가 없어 **확정하지 못했다**.
- CUBRID PR: 컴파일(클라이언트, `xasl_generation.c`·`type_checking.c`)은 develop 과 같은 도메인을 정하고 값이 있어야 정해지는 자리만 GATE 슬롯으로 둔다.
  로드(`stream_to_xasl.c → domain_plan.c stx_build_domain_plan`)가 불변 `DOMAIN_PLAN` 을 1회 도출하고, 실행마다 `domain_resolve.c qexec_resolve_domains`
  가 `XASL_STATE.resolved_domain` 에 결정을 쓴다(`domain_plan.h:20-48` 개요). 행은 읽기만 한다.

**같은 점:** 둘 다 "플랜/명령에 캐스트를 미리 싣고 행은 그 캐스트를 실행만 한다". **다른 점:** 저쪽은 그 '미리'가 플랜 수명 1회, 우리는 실행 1회.

## 2. 바인드(값 없는 자리)의 처리

| | database-reference 참고 | CUBRID PR#8022 |
|---|---|---|
| 파싱 시 타입 | `ExpnBindParameter()` 생성자에서 `set_meta(DBType::UNKNOWN)` (`expn_bind_parameter.cc:25`) | `TYPE_POS_VALUE` + `DB_TYPE_VARIABLE` |
| 연산 메타 | `_MetaEvalOperatorMulResult`: `type_L==UNKNOWN || type_R==UNKNOWN → SetUnknown()` (`compile_and_meta_eval_operator_impl.h:47` 등 6곳) | 게이트의 bind step 이 바인드 값 타입으로 변수 POS 의 도메인을 정하고(`qexec_share_value`), late-binding 노드를 producer 순으로 해석 |
| 함수 인자 검사 | `_arg_type_check_unknown`: UNKNOWN 이면 결과도 UNKNOWN 으로 두고 검사 생략 (`compile_and_meta_eval_function.h:44-50`); `_arg_type_check` 는 `IsConvertibleType` 실패 시 **컴파일 오류** `EXTERNAL_ERROR_EXP_FN_ARG_TYPE` | 바인드 값이 있으니 게이트에서 변환 셀을 고르고 실패하면 **실행 전 오류**(-454/-181/-539/-1118) |
| 클라이언트가 보내는 바인드 | 타입을 **동반**한다(`sql_processor_handler.h:77-105` `Bind*` 가 `pair<str, DBType>`) | 값(DB_VALUE)이 타입을 들고 온다 — 같은 성질 |

**읽는 법:** database-reference 참고가 UNKNOWN 을 전파하는 것은 "컴파일에서 못 정하면 미룬다"는 뜻이지 "행에서 정한다"는 뜻이 아니다. 어디서 받는지는 헤더에 없다.
CUBRID PR 의 게이트는 그 '미룬 것'을 받는 자리를 **명시적으로 하나로** 만든 것이고, 이 점은 참고보다 명확하다.

## 3. 조합표·변환표

- database-reference 참고: `db_type_util.h:15` `enum DB_OPD_COMB_TYPE`(NUMBER_X_NUMBER … DATE_X_DATE …), `db_meta_util.h:32-35` `GetPlus/Minus/Multiply/DivisionDBMeta(comb)`.
  결과 정밀도는 최대치로 고정(`SetNumber(NUMBER_PREC_MAX, SCALE_NULL)`). 옵티마이저 비용표도 같은 조합 축을 쓴다(`expression_cost_calculator.h:1170 ARITH_CODE[..][DB_OPD_COMB_MAX]`).
  `IsConvertibleType(t1,t2)`·`GetDistance(t1,t2)`·`GetDatetimeCompareType(t1,t2)` 는 선언만 있고 구현 `.cc` 가 트리에 없다.
- CUBRID PR: `object_domain_convert.cpp` 가 `tp_value_cast_internal` 의 타입쌍 본문을 셀 함수로 뽑은 정적 변환 표(모드 ASSIGN/IMPLICIT/COMPARE/OPERAND), `domain_rules.c` 가 산술·비교 방향·공통값·집계·collation 병합 규칙.
  값 하나하나는 여전히 자기 타입을 들고 다닌다(`DB_VALUE` 자기 서술) — 참고의 "값은 타입 없음, 메타와 관례로 짝" 과 다른, 우리가 앞선 안전성(expc 비교 §6 과 동일 판정).

## 4. collation

database-reference 참고에는 표현식 단위 collation 이 없다 — `parser.cc:3075` "TODO: COLLATE 구문이 오면 sort key 는 character string 이어야 한다"(미지원), 정렬 규칙은 `common/datatype/nls/nls_sort.cc` 의 NLS 전역 설정.
따라서 PR 스펙 변경 5(ELT 가지 collation 병합)는 **대조 불가**. PR 의 병합 규칙은 새 발명이 아니라 CUBRID 의 기존 `LANG_RT_COMMON_COLL`(코드셋 공통 collation, concat 과 같은 규칙)이고 병합 불가면 행에서 -1150 이다(`pr.diff` 28587-28617). 즉 "행이 고른 가지의 collation" 이라는 **develop 의 비결정성**을 기존 규칙으로 닫은 것이라 방향은 맞다. 매뉴얼에 적을 문구가 필요할 뿐이다.

## 5. 대조가 안 되는 것 (정직하게 적어 둔다)

- UNION 열 타입 통일: `LpNodeSet.setcol_` 목록과 `//해당 변수들은 아직 분석이 되지않아서 주석처리한다` 뿐. 규칙 없음 → PR 스펙 변경 4 는 참고 근거 없음.
- MEDIAN/PERCENTILE 입력 타입: `kMedian → PERCENTILE_CONT_AN`(동일 기본함수)만 확인. 함수 메타평가 표에서는 `MetaEvalFunctionError`(분석 함수 경로에서 처리). 인자 타입 규칙 미확인 → 스펙 변경 2 는 "한 함수·한 규칙" 방향만 일치.
- 세션변수: 서버 트리에 개념 없음 → 스펙 변경 3 대조 불가.
- 실행 시점의 UNKNOWN 해소(`GenerateExecutorCm`·`CursorBind`): 헤더에 단계 이름만 있고 본문 없음.

## 6. PR#8022 리뷰에 쓴 결론

1. **설계 방향은 참고와 일치**한다(행에서 정하지 않는다). 불변조건 5개를 흔들지 않는다는 10-02 판정을 뒤집을 근거 없음.
2. **결정 시점이 다른 이유를 코드에 적어야 한다** — `domain_plan.h` 개요에 "왜 컴파일이 아니라 실행 직전인가"(prepare 에 바인드 타입 없음·클론 공유·캐시 키) 한 문단 (지적 D1-01, 🟢 문서 제안).
3. **실행당 1회의 비용은 설계상 감수한 것이므로 수치로 보여야 한다** — 참고는 플랜당 1회라 비교 기준이 분명하다. OLTP 셀의 cycles/instructions/LLC-miss 반복 측정 요청(지적 M-01, MEAS-04/06/07).
4. collation 병합은 기존 규칙 재사용이므로 지적 아님 — 매뉴얼 문구만.

## 출처

- database-reference 참고: `include/server/module/expression_eval/compile_and_meta_eval/*.h`, `include/server/module/datatype/db_type_util.h`, `db_meta_util.h`,
  `include/server/dbsvr/module/sql_compiler/expression/expn_bind_parameter.h`, `server/dbsvr/module/sql_compiler/expression/expn_bind_parameter.cc`,
  `include/server/dbsvr/module/sql_processor/sql_processor.h`, `sql_processor_handler.h`, `include/server/module/executor/cursor/cursor_dbsvr.h`,
  `include/server/module/executor/task/execute_task_ssvr.h`, `include/server/dbsvr/module/sql_compiler/transformer/lp/lp_node_set.h`,
  `expn_fn_aggr_util.h`, `server/dbsvr/module/sql_compiler/parser/syntax/parser.cc`, `common/datatype/nls/nls_sort.cc`.
- CUBRID: PR#8022 head `cb0514bb7` — `src/query/domain_plan.h`(개요 20-48), `domain_resolve.c`(단계 주석 2630-2660), `domain_state.h`, `pr.diff` 28587-28617(collation).
- 관련 문서: [expc-식컴파일러-비교.md](expc-식컴파일러-비교.md) §1 "타입 결정" 행, §6 값 표현. 리뷰 산출물: `claude-workspace/projects/CBRD-27510/리뷰보고서-PR8022.md`.
