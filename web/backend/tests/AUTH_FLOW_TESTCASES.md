# Login / Register — HTTP·UI error matrix

백엔드는 FastAPI 기준이며, 검증 실패 시 **422**와 `detail`(문자열 또는 객체 배열)을 반환합니다. 프론트는 `lib/api.ts`의 `formatApiErrorMessage`로 표시 문구를 정리합니다.

## Register `POST /api/auth/register` (JSON)

| # | 조건 | 기대 HTTP | 비고 |
|---|------|-----------|------|
| R1 | `{ login_id, name, password }` | 201 | DB `users.email`에 ID 저장 |
| R1b | 레거시 `email` / `username` / `userId` 키 | 201 | 라우터가 dict로 받은 뒤 `user_create_from_register_body()`에서 `login_id`로만 `UserCreate` 검증 (Pydantic에 `email` 키 미전달) |
| R1c | 프론트는 `login_id`만 전송 + `skipAuth`로 `Authorization` 미포함 | 201 | 구 토큰으로 인한 이상 동작 방지 |
| R2 | 동일 ID 재가입 | 400 | `This ID is already registered` → UI: 이미 사용 중인 ID |
| R3 | 필수 필드 누락 (예: `password` 없음) | 422 | Pydantic `Field required` |
| R4 | 빈 JSON `{}` | 422 | 다수 필드 누락 |
| R5 | `password` 길이 > 100 | 422 | `String should have at most 100 characters` |
| R6 | ID/이름 공백만 (trim 후 빈 문자열) | 422 | `str_strip_whitespace` 후 `min_length` 위반 |
| R7 | 잘못된 JSON 본문 | 422 | 파싱/검증 오류 |

## Login `POST /api/auth/login` (application/x-www-form-urlencoded)

OAuth2 폼 필드: `username`(로그인 ID), `password`.

| # | 조건 | 기대 HTTP | 비고 |
|---|------|-----------|------|
| L1 | 등록된 ID + 올바른 비밀번호 | 200 + `access_token` | |
| L2 | 틀린 비밀번호 | 401 | `Incorrect ID or password` |
| L3 | 없는 ID | 401 | 동일 메시지 (계정 존재 여부 노출 최소화) |
| L4 | `username` 또는 `password` 누락 | 422 | 폼 검증 |
| L5 | `Content-Type: application/json` 로 전송 | 422 | 폼 파서와 불일치 |

## 인증이 필요한 API

| # | 조건 | 기대 HTTP |
|---|------|-----------|
| A1 | 유효 Bearer 토큰 | 200 |
| A2 | 토큰 없음 | 401 |
| A3 | 잘못된/만료 토큰 | 401 |

## 프론트엔드 (register / login 페이지)

- 빈 필드·공백만 ID/이름: 클라이언트에서 먼저 차단 (`trim` 후 검사).
- 네트워크 실패: `ApiError` 메시지 한국어 안내.
- 422: `detail` 배열을 필드 라벨(ID/이름/비밀번호)과 짧은 한국어 설명으로 합침.

## 자동 점검

`pytest tests/test_auth_api.py` (기본 SQLite 인메모리, `TEST_DATABASE_URL`로 PostgreSQL 지정 가능).
