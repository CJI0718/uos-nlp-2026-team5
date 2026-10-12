# 처음 하는 GitHub 협업

## 다섯 용어만 알면 시작할 수 있어요

| 용어 | 여기서의 뜻 |
| --- | --- |
| Repository (repo) | 프로젝트의 공용 파일함 + 변경 이력 |
| Issue | 한 가지 질문이나 할 일을 담은 토론 카드 |
| Branch | main을 바로 바꾸지 않고 작업하는 별도 작업 공간 |
| Commit | 어떤 변경을 했는지 설명을 붙여 남긴 저장 지점 |
| Pull request (PR) | 내 변경을 공용 main에 합치기 전 검토받는 제안 |

main은 팀이 함께 확인한 기준본으로 씁니다. Google Docs처럼 동시에 같은 문장을 편집하는 방식과는 다릅니다.

## 리서치부터 시작하는 가장 쉬운 방법

1. Issues → New issue에서 연구 아이디어 양식을 고릅니다.
2. 관심 있는 후보 ID, 궁금한 점, 논문 링크, 다음 확인 항목을 적습니다.
3. 팀원이 댓글로 질문하거나 근거를 추가합니다.
4. 합의된 내용만 docs/decisions에 남깁니다.

긴 문서는 파일로, 토론은 Issue로, 확정된 결론은 decisions로 구분하면 찾기 쉽습니다.
주제가 확정되기 전에는 후보 하나를 확정된 방향처럼 README에 쓰지 않습니다.

## 웹에서 문서 한 개 수정하기

1. 저장소의 수정할 Markdown 파일을 엽니다.
2. Edit(연필)로 수정하고 Preview로 확인합니다.
3. Commit changes에서 **새 branch를 만들고 PR을 여는 선택지**를 고릅니다.
4. branch 이름 예: docs/memory-paper-notes
5. PR에 바꾼 이유, 확인한 내용, 남은 질문을 적습니다.
6. 다른 팀원이 변경 사항을 확인하고, 합의 후 merge합니다.

UI 문구는 바뀔 수 있습니다. 핵심은 main 직접 수정 대신 새 branch → PR입니다.

## PC에서 개발할 때

Git 인증은 각자 계정으로 합니다. API 키를 GitHub 로그인 정보 대신 넣지 않습니다.

```powershell
git clone https://github.com/CJI0718/uos-nlp-2026-team5.git
cd uos-nlp-2026-team5
git switch main
git pull --ff-only
git switch -c docs/topic-comparison
```

원하는 파일을 수정하고 변경 내용을 확인한 뒤, **실제로 수정한 파일 경로를 지정해서** git add, git commit, git push를 사용합니다.
처음에는 무조건 git add .을 하기보다 파일을 하나씩 확인하는 편이 안전합니다.

```powershell
git status
git diff
git add docs/research/README.md
git commit -m "docs: clarify research comparison questions"
git push -u origin docs/topic-comparison
```

위 예시는 해당 파일을 실제로 수정한 경우에만 실행합니다. push 후 GitHub에서 PR을 열어 검토받습니다.
작업 중 파일이 있으면 branch 전환·pull 전에 상태를 확인합니다. 충돌이 나면 reset --hard나 force push로 덮어쓰지 말고 함께 해결합니다.

## 작은 팀의 운영 규칙

- 한 Issue에는 목적·담당자·완료 기준을 적습니다. 담당자는 팀에서 합의합니다.
- 한 branch/PR에는 관련된 한 묶음의 변경만 담습니다.
- 문서·코드의 같은 부분을 두 사람이 동시에 크게 고치기 전에는 Issue에서 조율합니다.
- PR은 다른 팀원 1명이 확인하는 것을 운영 원칙으로 합니다. 서버에서 강제되는 보호 규칙이 설정됐다는 뜻은 아닙니다.
- 혼자 확인해야 하는 긴급 수정은 이유와 검증 내용을 기록합니다.
- 실패한 실험을 삭제하거나 성공 사례만 모으지 않습니다.
- 인증 정보와 개인정보가 보이면 push하지 말고 먼저 제거합니다. 이미 유출됐다면 해당 키 폐기·재발급이 우선이며 파일 삭제만으로 해결되지 않습니다.
- AI가 생성한 설명과 코드도 사람이 출처·정답·실행 결과를 검토합니다.

## 팀원 초대

소유자: Settings → Collaborators → Add people → 팀원 GitHub 사용자명 선택 → 초대.
팀원이 수락한 뒤 쓰기 권한으로 작업할 수 있습니다. 공개 링크 공유만으로 쓰기 권한이 생기지는 않습니다.

## 참고

- [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow)
- [협업자 초대](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)
