# pl_engine

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

Gradle 기반 Java PL 엔진 — 별도 프로세스로 실행되며 Unix 도메인 소켓으로 `cub_server`와 통신.
진입점 `com.cubrid.jsp.Server`. `com.cubrid.jsp`(SP 런타임: protocol/value/jdbc/classloader 등),
`com.cubrid.plcsql`(PL/CSQL 컴파일러: ast/visitor/type). PL/CSQL 파싱은 ANTLR 4.9.3
(`pl_server/src/main/antlr/`). 빌드: `ninja pl_server` 또는 `./gradlew build`.
(경로 접두사: `pl_engine/pl_server/src/main/java/`)

| 함수/클래스 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `Server.main` | `com/cubrid/jsp/Server.java:262` | PL 엔진 프로세스 진입점(싱글턴 `serverInstance` :64) | `cub_server`가 프로세스 기동(`src/sp/pl_sr*.cpp`) |
| `ListenerThread.run` | `com/cubrid/jsp/ListenerThread.java:63` | 소켓 수신 루프 — 접속마다 `ExecuteThread` 생성(:74) | `Server` 기동 시퀀스 |
| `ExecuteThread.run` | `com/cubrid/jsp/ExecuteThread.java:128` | 요청 단위 SP 실행 루프(wire protocol 처리) | `ListenerThread` |
| `StoredProcedure.invoke` | `com/cubrid/jsp/StoredProcedure.java:322` | 대상 Java 메서드 리플렉션 호출·`Value` 반환 | `ExecuteThread` 실행 경로 |
| `TargetMethod` | `com/cubrid/jsp/TargetMethod.java` | 시그니처→Java 메서드 해석 | `StoredProcedure` |
| `ServerConfig` / `SysParam` | `com/cubrid/jsp/ServerConfig.java`, `SysParam.java` | 엔진 설정/시스템 파라미터 로드 | `Server` 초기화 |
| `PlcsqlCompilerMain.compilePLCSQL` | `com/cubrid/plcsql/compiler/PlcsqlCompilerMain.java:76` (+오버로드 :81) | PL/CSQL 소스 → Java 코드 컴파일(`CompileInfo`) | 서버의 SP 컴파일 요청(`src/sp/pl_compile_handler.cpp` 경유 프로토콜) |
| `ParseTreeConverter` | `com/cubrid/plcsql/compiler/ParseTreeConverter.java` | ANTLR 파스 트리 → AST 변환 | `PlcsqlCompilerMain` |
| `com.cubrid.jsp.value.*` | `com/cubrid/jsp/value/` | SQL↔Java 값 변환 계층 | `ExecuteThread`/`StoredProcedure` 마샬링 |
| `com.cubrid.jsp.protocol.*` | `com/cubrid/jsp/protocol/` | `cub_server`와의 wire 프로토콜(패킹/언패킹) | `ExecuteThread` |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: pl_engine/AGENTS.md 증류)

### 모듈 일반

- **Java 8 타깃 — Java 9+ API 사용 금지** (JDK 1.8+ 툴체인).
- PL 엔진이 떠 있어야 SP가 실행된다.
- JDBC 의존성은 로컬 서브모듈 경로 또는 CUBRID Maven 리포에서 해석.
- 주요 의존성: junixsocket 2.8.3, Netty 4.1.115, JUnit Jupiter 5.9.1, Apache Commons.
- `google-java-format` CI 강제. Gradle Kotlin DSL. Fat JAR 패키징.
- ✅ **리뷰 체크포인트**: Java 9+ API(예: var, List.of 등)가 들어오지 않았는가?
- ✅ **리뷰 체크포인트**: 포맷이 google-java-format을 통과하는가?
- ✅ **리뷰 체크포인트**: 새 테스트가 JUnit 5(Jupiter)로 작성됐는가?

### PlcsqlCompilerMain.compilePLCSQL (com/cubrid/plcsql/compiler)

- ANTLR 문법 변경 후 `./gradlew generateGrammarSource` 필요.
- ✅ **리뷰 체크포인트**: ANTLR 문법 수정 시 생성 소스 재생성이 수반됐는가?

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- (현재 등록된 예비 이슈 없음)

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)

### .51
- (해당 없음 또는 미기입)

### .52
- (해당 없음 또는 미기입)
