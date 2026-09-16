# 정소희 — 관리 공간 (소스 분석)

GitHub `soheejung-cs` · JIRA `soheejung` · 컨테이너 **.50 / .51 / .52** (hostname 은 셋 다 `sohee`, `hostname -I` 로 구분)

## 컨테이너 배치 (요약 — 정본은 `claude-workspace/hosts/{50,51,52}.md`, CLAUDE.md 가 여기서 만들어진다)
| 컨테이너 | 역할 | 벤치 | 특기 사항 |
|---|---|---|---|
| **.50** | TPC-H SF10 보유 · JOB 재적재본 | JOB + TPC-H | tpch 스크립트 정본 |
| **.51** | 원본 환경 · **dev4-ai-source 병합 허브** · 8825(소스노트 사이트)/8826(agent-todo 보드) 호스팅 | JOB 51G(원본 보유) | debug·release 상시, `.51 → .52` SSH 단방향 |
| **.52** | JOB 측정 하네스 원산지(`job_confirm.sh` 등) | JOB | `load_joinorder.sh` 원산지 |
셋이 같은 리포들을 push 하므로 세션 시작에 `git pull --rebase` (claude-workspace · dev4-review-workspace · dev4-ai-source).

## 진행 중 (소스 분석이 딸린 이슈)
| 이슈 | 상태 | 환류 |
|---|---|---|
| CBRD-27369 / PR#7900 — UPDATE STATISTICS 직렬화·무잠금 히스토그램 읽기 | 리뷰 라운드 2 대응 완료(`a910e8e6e`), Q1~Q4 결정 대기 | `staging/정소희-CBRD-27369.md` (10건) |
| CBRD-27429 / PR#7957 — V0 통계 레이아웃 제거 | 진행 중 (보드 #98) | — |
| CBRD-27215 / PR#7658 — 식 평가 컴파일 | 진행 중 (보드 #55) | — |
| CBRD-27126 / PR#7561 — 비용 상수 파라미터화 | 진행 중 (보드 #32) | — |
프로젝트 문서는 `claude-workspace/projects/CBRD-*/`, 보드는 http://192.168.6.51:8826/.

## 담당
- 하루 1회 `staging/*.md` → 모듈 §2·§3 환류 배치, `python3 tools/gen_site.py`, 8825 사이트 재생성(.51).
- 다른 컨테이너/팀원의 모듈 노트 기여 병합.
