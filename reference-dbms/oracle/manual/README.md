# Oracle 매뉴얼 원문 보관소 (요청 시에만 읽는다)

여기에 Oracle 공식 매뉴얼을 **책(book) 단위 디렉터리**로 올린다. 에이전트는 통째로 읽지 않는다 —
`toc.md` 로 항목을 찍어 **해당 절 파일만** 연다(규약: `dev4-review-workspace/skills/oracle-reference`).

```
manual/
  README.md
  <책약칭>/              예: sql-language-reference, concepts, admin-guide, tuning-guide
    toc.md               목차 — "절 제목 → 파일명(#anchor)" 한 줄씩. 없으면 에이전트가 1회 생성해 커밋
    <장번호>-<slug>.md|.html|.txt   장(또는 절) 단위 파일. PDF 라면 장 단위로 쪼개 텍스트로
```

- 형식: **텍스트로 grep 되는 것**(.md/.html/.txt)이 최선. PDF 는 통째로 올리지 말고 `pdftotext -layout` 결과를 장별로.
- 한 파일 50MB 미만(GitHub 제한), 리포 전체가 커지면 별도 리포 `dev4-oracle-manual` 로 분리해 서브모듈로 건다.
- 버전을 파일 첫 줄 또는 `toc.md` 머리에 적는다(예: `Oracle Database 19c, E96310-xx`).
- 라이선스: Oracle 문서는 재배포 제한이 있으므로 **리포는 private 유지**.
