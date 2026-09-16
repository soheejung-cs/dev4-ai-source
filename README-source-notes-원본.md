# CUBRID 소스 분석 창고

기준: upstream/develop `95b79e7ed` (2026-08-26). 리포 22개 AGENTS.md의 증류 + 세 컨테이너(.50/.51/.52)의
축적 지식 합본. **리포 AGENTS.md가 소스 지식의 1차 정본**이고, 이 문서는 그 위에 컨테이너들이 실측·리뷰로
얻은 "주의점·리뷰 체크포인트"를 모듈별로 얹은 것이다. 갱신 규약: develop 큰 변경 후 리비전 갱신, 새 지식은 해당
모듈의 "축적 지식"에 출처(.5x)와 함께 추가, 재검증 실패는 삭제가 아니라 명시. **하루 1회 컨테이너 간
공유**(2026-08-26 지시): .51이 병합 허브 — 피어 기여 병합 → 아티팩트 재게시 + .52 scp.

✔ 3컨테이너 병합 완료(2026-08-26): .50 102건(optimizer 60·query 29·cross 6·storage 5·base 1·thread 1,
  기준 CBRD-27094@faf5a3b2a — develop과 다른 항목은 각 절에 명시), .51, .52.
⚠ AGENTS.md는 git 추적 파일 — 이 창고의 발견으로 AGENTS.md를 고칠 때는 별도 커밋/PR로 분리하고
  사용자 확인 후 진행(예: AGENTS.md의 "비용 추정=plan_generation.c" 오안내는 정정 후보).
⚠ .52 지식의 기준 리비전은 develop faf5a3b2a 시점 + 명시 브랜치. `c44ccf767`(btree start_col UB 수정)은
  **develop 미반영**, `px_scan_slot_iterator.cpp:124` 선택도 버그는 **미수정** 상태다.


## 리포 구성

- [common.md](common.md) — 전 모듈 공통 (AGENTS.md 증류)
- [build-link.md](build-link.md) — 빌드·링크 구성 (모듈 횡단)
- [cross.md](cross.md) — 모듈 경계 지식
- [measurement.md](measurement.md) — 측정 방법론
- `modules/` — 모듈별 3부 구조 (2026-08-26 사용자 지시):
  **§1 소스 목적 및 사용처(함수별)** / **§2 분석 내용(함수별** — 주의점·리뷰 체크포인트·축적 지식**)** /
  **§3 예비 이슈 사항**(미수정 버그·의심·정정 후보 — 해소 시 삭제가 아니라 "해소됨" 갱신)
- [src/base](modules/src-base.md)
- [src/storage](modules/src-storage.md)
- [src/transaction](modules/src-transaction.md)
- [src/query](modules/src-query.md)
- [src/xasl](modules/src-xasl.md)
- [src/optimizer](modules/src-optimizer.md)
- [src/parser](modules/src-parser.md)
- [src/compat](modules/src-compat.md)
- [src/object](modules/src-object.md)
- [src/executables](modules/src-executables.md)
- [src/loaddb](modules/src-loaddb.md)
- [src/method](modules/src-method.md)
- [src/sp](modules/src-sp.md)
- [pl_engine](modules/pl_engine.md)
- [src/broker](modules/src-broker.md)
- [src/connection](modules/src-connection.md)
- [src/communication](modules/src-communication.md)
- [src/thread](modules/src-thread.md)
- [src/monitor](modules/src-monitor.md)
- [unit_tests](modules/unit_tests.md)
- `site/` — **페이지별 웹 뷰** (모듈·문서마다 별도 HTML). `tools/gen_site.py`로 md에서 재생성:
  `python3 tools/gen_site.py`. 내부망 호스팅: `.51`에서 `http://192.168.6.51:8825/`
  (`python3 -m http.server 8825 --bind 0.0.0.0 --directory site`). **아티팩트는 만들지 않는다**
  (2026-08-27 사용자 지시 — 내부망 호스팅으로 대체).

## 공유 규약 (2026-08-26 사용자 지시)

- **하루 1회 컨테이너(.50/.51/.52) 간 공유.** 이 리포가 정본, 세 컨테이너 모두 같은 계정
  (soheejung-cs)으로 pull/push한다.
- 새 발견은 해당 모듈 파일의 "축적 지식"에 **출처(.5x)·기준 리비전** 표기로 추가.
- **재검증 실패는 삭제가 아니라 명시** ("행번호 확인 필요 — 현재 소스와 불일치" 식).
- 리포의 AGENTS.md 증류부와 실제 코드가 다르면 코드가 정답. 리포 대문서(AGENTS.md) 수정은
  별도 커밋/PR + 사용자 확인 후.
- 보낼 게 없으면 "없다"고 답한다(무응답과 누락 구분).
