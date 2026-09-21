# 레퍼런스 인스턴스 실측 재현 스크립트

`modules/src-optimizer.md` · `staging/정소희-JOB-비용모델.md` 의 **"database-reference 참고"** 항목들이
어떤 실측에서 나왔는지 되짚기 위한 것. 주장만 남고 재현 방법이 사라지면 나중에 검증이 불가능해진다.

- 대상: 레퍼런스 인스턴스 `192.168.6.11:5432`, DB `postgres` (접속 정보는 메모리 `PG레퍼런스-접속.md`)
- 실행: `python3.11 <파일>` — 드라이버는 `pg8000`(`python3.11 -m pip install --user pg8000`)
- **읽기 전용**이다. `SET` 은 세션 한정이고 데이터를 바꾸지 않는다.

| 파일 | 무엇을 확인하나 | 어느 항목의 근거 |
|---|---|---|
| `par_costing.py` | 병렬 GUC 기본값, 워커 4 허용 ↔ 금지 플랜의 비용 대조 | 병렬을 비용에 넣는가 |
| `par_decision.py` | `parallel_setup_cost` 를 올리면 직렬로 뒤집힘 · 워커 수는 크기 휴리스틱 · CPU 만 워커로 나눔 | 같음 |
| `par_flip_point.py` | 뒤집히는 정확한 지점을 이분탐색 → `add_path` 의 1% fuzz factor 노출 · 워커 계단·비용 분해 검산 | 같음 |
| `join_sel_mcv.py` | 필터로 1행이 된 차원을 팩트와 조인할 때의 추정 vs 실제 · 상수 질의와의 대조 · 양쪽 통계(MCV/n_distinct) | 조인 선택도의 값-조건화 부재 |

⚠ 수치를 노트에 옮길 때 **제품명을 쓰지 않는다** — 규약은 메모리 `rules/참조DB-표기.md`.
