# dev4-ai-source — CUBRID 소스 분석 지식 정본

`cubrid-source-notes`(@`8e22c700d`)를 2026-09-16 에 통째로 이관했다. **소스 분석에 관한 것은 전부 여기에** 쓴다.
리뷰 방식은 `dev4-review-workspace`, 일하는 방식·프로젝트 문서는 `claude-workspace`.

```
skills/source-learning/SKILL.md   소스 학습·기록 규약 — 어디에(§1~§4/대기소), 무엇을(검증 기준), 어떤 형식으로
staging/환류대기.md               아직 모듈에 반영하지 않은 검증된 사실 (하루 1회 배치)
modules/src-*.md                  모듈별 4부: §1 목적·사용처 / §2 분석 / §3 예비 이슈 / §4 진행 중
common.md · cross.md · measurement.md · build-link.md   모듈 횡단 주제
tools/gen_site.py                 site/ 정적 뷰 생성 (.51 이 http://192.168.6.51:8825/ 로 호스팅)
README-source-notes-원본.md       이관 전 리포의 README (구조 설명·기여 규약)
```

소스 *구조* 는 엔진 리포 `AGENTS.md` 가 1차 정본 — 거기 있는 것은 여기 적지 않는다.
각 컨테이너: `git clone https://github.com/soheejung-cs/dev4-ai-source ~/dev/docs/dev4-ai-source`.
