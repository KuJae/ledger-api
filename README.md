# 가계부 API (ledger-api)

**GitHub:** _push 후 기입_ · **Render 배포 URL:** _배포 후 기입_ · Swagger UI: `<배포 URL>/docs`

클라우드컴퓨팅실습 4주차 실습 기록입니다.
FastAPI + SQLAlchemy를 **Supabase(클라우드 PostgreSQL)** 에 연결해 계좌·거래·카테고리를 저장·조회·집계하고,
그 API를 Render에 배포했습니다. 앱은 Render에, 데이터는 Supabase에 있어 **서비스가 잠들었다 깨어나도 데이터가 남습니다**
(3주차 임시 리스트와 다른 점).

## 엔드포인트

| 메서드 | 경로 | 하는 일 | 성공 코드 |
| --- | --- | --- | --- |
| POST | `/accounts` | 계좌 생성 | 201 |
| GET | `/accounts` | 계좌 목록 | 200 |
| GET | `/accounts/{id}` | 계좌 단건 (없으면 404) | 200 |
| POST | `/transactions` | 거래 생성 (계좌 없으면 404) | 201 |
| GET | `/accounts/{id}/detail` | 계좌 + 거래 **중첩** 응답 | 200 |
| GET | `/stats/by-category` | 카테고리별 지출 합계 (GROUP BY) | 200 |

명세는 따로 쓰지 않았습니다 — FastAPI가 `/openapi.json`으로 자동 생성합니다.

## 데이터베이스 스키마

```text
accounts (id, name, balance)
    │ 1
    │        ← relationship(back_populates), cascade="all, delete-orphan"
    │ N
transactions (id, account_id→accounts.id, category_id→categories.id, amount, memo, occurred_at)
                                  │ N
                                  │ 1
                           categories (id, name UNIQUE, kind)
```

- 거래는 계좌를 **반드시**, 카테고리는 **있으면** 가리킵니다(`category_id`는 NULL 허용)
- `occurred_at`은 `server_default=func.now()` — 시각 기준을 각자의 PC가 아니라 DB 서버 하나로 고정

## 프로젝트 구조

```text
ledger-api/
├── database.py        # Engine · SessionLocal · Base · get_db (echo=True)
├── models.py          # Account · Category · Transaction (ORM)
├── schemas.py         # Pydantic 입력/출력 스키마
├── main.py            # 앱 생성 + 테이블 생성 + 경로 6개
├── requirements.txt   # Render 가 설치할 패키지
├── render.yaml        # Render 배포 설정
├── .env.example       # DATABASE_URL 형식 (실제 .env 는 Git 제외)
└── .gitignore
```

## 로컬에서 실행하기

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # DATABASE_URL 을 본인 Supabase 값으로 채운다
uvicorn main:app --reload          # http://127.0.0.1:8000/docs
```

`.env`에 연결 문자열이 없으면 **오류 없이** `sqlite:///./ledger.db`로 넘어갑니다.
폴더에 `ledger.db`가 생겼다면 Supabase가 아니라 로컬 SQLite에 저장된 것입니다.

---

## 실습 기록

### ① 결과 확인

<!-- Supabase Table Editor 캡처를 여기에 붙이세요 (로그인된 브라우저가 필요합니다) -->

Supabase에 연결해 테이블 세 개가 생성되고, API로 넣은 계좌·거래가 그대로 저장되는 것을 확인했습니다.

```console
# 접속 확인 — 비밀번호는 ***로 가려진다
$ python -c "import database; print(database.engine)"
Engine(postgresql+psycopg://postgres.<프로젝트ref>:***@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres)

# 서버 PostgreSQL 17.6, 코드가 만든 테이블 세 개
public 테이블: ['accounts', 'categories', 'transactions']

# 계좌 생성 — 201
$ curl -X POST .../accounts -H 'Content-Type: application/json' \
       -d '{"name":"월급통장","balance":1500000}'
{"id":1,"name":"월급통장","balance":1500000}

# 없는 계좌 조회 — 404
$ curl -i .../accounts/999
HTTP/1.1 404 Not Found
{"detail":"계좌를 찾을 수 없습니다"}

# 거래 생성 — 201 (occurred_at 은 DB 서버가 채운다)
$ curl -X POST .../transactions -H 'Content-Type: application/json' \
       -d '{"account_id":1,"category_id":1,"amount":-12000,"memo":"점심"}'
{"id":1,"account_id":1,"amount":-12000,"memo":"점심","occurred_at":"2026-10-07T11:28:22.552032"}

# 없는 계좌에 거래 — 404 (DB 외래키가 막기 전에 미리 확인해 친절한 메시지)
$ curl -i -X POST .../transactions -d '{"account_id":999,"amount":-1}'
HTTP/1.1 404 Not Found
{"detail":"해당 계좌가 없습니다"}

# 중첩 응답 — 계좌 하나를 요청했는데 거래 목록이 딸려 온다
$ curl .../accounts/1/detail
{"id":1,"name":"월급통장","balance":1500000,
 "transactions":[{"id":1,"amount":-12000,"memo":"점심",...},
                 {"id":2,"amount":-1500,"memo":"지하철",...}]}

# 카테고리별 집계 — 단계 1의 GROUP BY 와 같은 질의
$ curl .../stats/by-category
[{"category":"교통","total":-1500,"count":1},
 {"category":"식비","total":-12000,"count":1}]
```

### ② 핵심 개념 되새김

- **계좌와 거래를 두 테이블로 나눈 이유 (1:N)** — 계좌 하나에 거래가 여러 개 달린다.
  거래마다 계좌 이름을 복사해 두면 이름 하나를 고칠 때 모든 거래를 함께 고쳐야 하고,
  한 줄이라도 빠지면 같은 계좌가 둘로 갈라진다. 그래서 거래는 번호(`account_id`)만 가리키고
  이름이 필요할 때 JOIN으로 붙인다.
- **모델 클래스와 실제 테이블의 대응** — `class Account(Base)` 하나가 `accounts` 테이블 하나다.
  `__tablename__`이 테이블 이름이 되고, 타입 표기가 그대로 제약이 된다 —
  `Mapped[str]`은 NOT NULL, `Mapped[str | None]`은 NULL 허용. `Base.metadata.create_all()`이
  이 정의를 읽어 `CREATE TABLE`을 대신 만든다.
- **접속 문자열을 `.env`로 분리하는 이유** — 그 한 줄에 DB 비밀번호가 들어 있어 코드에 적으면
  저장소에 그대로 공개된다. 또 로컬과 배포의 접속 정보가 달라도 코드는 그대로 두고 이 값만 바꾸면 된다.
  로컬은 `.env`, Render는 환경변수에서 읽고, `os.getenv("DATABASE_URL")`은 어느 쪽이든 똑같이 읽는다.

### ③ 자유 로그

단계 1에서 SQL을 직접 써 본 게 뒤에 도움이 됐다. `step3_join_agg.py`의 `JOIN` + `GROUP BY`가
`/stats/by-category`의 `func.sum()` · `group_by()`와 같은 질의라는 걸 `echo=True` 로그로 대조할 수 있었다.
표현 도구만 파이썬으로 바뀐 것이다.

트랜잭션은 일부러 깨뜨려 봤다. 출금과 입금 사이에 `raise`를 넣으니 출금 UPDATE가 이미 실행됐는데도
`rollback`이 그것까지 되돌려 잔액이 그대로였다. "중간까지만 반영된 상태"가 없다는 게 이런 뜻이었다.

가장 오래 막힌 건 Supabase 접속이었다. `password authentication failed`가 계속 났는데, 원인 후보가
여럿이라(프로젝트 ref · 일시정지 · pooler 종류 · 비밀번호) 하나씩 지워 나갔다. 없는 ref로 일부러
접속해 보니 `ENOTFOUND tenant/user not found`가 나고 내 ref로는 `password authentication failed`가
나는 걸 보고, ref와 서버는 멀쩡하고 비밀번호만 틀렸다는 걸 확정할 수 있었다. 결국 Supabase에서
비밀번호를 재설정하니 바로 붙었다.

그 전에 `.env`가 빈 비밀번호로 만들어진 적도 있었다. bash용 `read -s -p` 명령을 zsh에서 써서
입력창이 안 뜬 채 넘어간 것이었다. 셸이 다르면 같은 명령이 다르게 동작한다.

아직 안 한 것: Alembic 마이그레이션(단계 6)과 이체·N+1·인덱스(단계 7)는 확장이라 넘겼다.
`create_all()`이 이미 있는 테이블의 컬럼은 못 바꾼다는 건 알겠는데, 실제로 운영 중 스키마를
바꿔야 할 때 어떻게 하는지는 아직 감이 없다.

**AI 사용** — Claude Code한테 워크북 단계 1~5를 그대로 따라 만들게 했다. 결과는 직접 호출해서
확인했다. 단계 1은 네 스크립트의 출력(JOIN 3건 · 집계 2건 · 이체 전후 잔액 · 롤백 후 잔액 불변)을
눈으로 봤고, API는 생성 201 · 없는 계좌 404 두 종류 · 중첩 응답 · 카테고리별 집계를 하나씩 호출해
상태 코드와 본문을 확인했다(위 ① 기록). 연결 문자열의 비밀번호는 AI에게 주지 않고 내가 직접
`.env`에 입력했고, AI는 `***`로 가려진 출력만 보고 진단했다.
