# FSONL

**Function-Styled Object Notation Lines**

각 줄의 레코드 타입이 선두에 즉시 드러나는 줄 단위 직렬화 포맷.

```
@schema rm(target: string, --force?: bool = false)
rm("tmp.log", force=true)
rm("/var/cache", force=false)
log("info", "server started")
```

## 설치

```bash
pip install fsonl
```

## 빠른 시작

### 인라인 스키마로 파싱

```python
import fsonl

text = """
@schema rm(target: string, --force?: bool = false)
rm("tmp.log")
rm("/var/cache", force=true)
"""

result = fsonl.loads(text)
for entry in result.entries:
    print(entry)
# {'type': 'rm', 'target': 'tmp.log', 'force': False}
# {'type': 'rm', 'target': '/var/cache', 'force': True}
```

### 코드 스키마로 파싱

```python
import fsonl

schema = fsonl.Schema.from_string(
    "@schema log(level: string, msg: string)"
)

result = fsonl.loads('log("info", "started")\n', schema=schema)
print(result.entries[0])
# {'type': 'log', 'level': 'info', 'msg': 'started'}
```

### Python 함수로 스키마 정의 (3.10+)

```python
import fsonl

schema = fsonl.Schema()

@schema.define
def rm(target: str, *, force: bool = False): ...

result = fsonl.loads('rm("tmp.log", force=true)\n', schema=schema)
print(result.entries[0])
# {'type': 'rm', 'target': 'tmp.log', 'force': True}
```

### 직렬화

```python
import fsonl

schema = fsonl.Schema.from_string(
    "@schema log(level: string, msg: string)"
)

print(fsonl.dumps({"type": "log", "level": "info", "msg": "hello"}, schema=schema))
# @schema log(level: string, msg: string)
# log("info", "hello")
```

### 파일 스트리밍

```python
import fsonl

with open("events.fsonl", newline="") as f:
    for entry in fsonl.iter_entries(f):
        print(entry)
```

### Raw 모드 (스키마 바인딩 없이)

```python
import fsonl

result = fsonl.loads_raw('x(1, "hello", flag=true)\n')
entry = result[0]
print(entry["type"])        # 'x'
print(entry["positional"])  # [1, 'hello']
print(entry["named"])       # {'flag': True}
```

## API

### 파싱

| 함수 | 설명 |
|------|------|
| `loads(text, *, schema, ignore_inline_schema, extra_fields)` | FSONL 텍스트 스키마 바인딩 파싱 |
| `load(fp, **kwargs)` | 파일 객체에서 스키마 바인딩 파싱 |
| `loads_raw(text)` | FSONL 텍스트 바인딩 없이 파싱 (Stage 1만) |
| `load_raw(fp)` | 파일 객체에서 바인딩 없이 파싱 (Stage 1만) |
| `iter_entries(source, *, schema, ignore_inline_schema, extra_fields)` | 바인딩된 엔트리 지연 이터레이터 |
| `iter_raw(source)` | Raw 엔트리 지연 이터레이터 |
| `bind(entry, schema, *, extra_fields)` | 단일 raw dict를 Schema에 바인딩 |

### 직렬화

| 함수 | 설명 |
|------|------|
| `dumps(entries, *, schema, allow_extra, exclude_schema)` | FSONL 텍스트로 직렬화 |
| `dump(entries, fp, *, schema, allow_extra, exclude_schema)` | 파일 객체에 직렬화 |

### 스키마

| 메서드 | 설명 |
|--------|------|
| `Schema.from_string(text)` | `@schema` 문자열로 생성 |
| `Schema.from_fsonl(text)` | FSONL 텍스트에서 `@schema` 추출 (비스키마 줄 무시) |
| `Schema.from_file(path)` | `.fsonl` 파일에서 `@schema` 로드 |
| `@schema.define` | 데코레이터: 함수 시그니처로 스키마 정의 (Python 3.10+) |
| `schema.add(text)` | `@schema` 정의 추가 |
| `schema.get(type_name)` | 타입 정의 조회 |
| `schema.has(type_name)` | 타입 정의 존재 여부 확인 |
| `schema.type_names()` | 정의된 모든 타입명 목록 |

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `ignore_inline_schema` | `False` | 콘텐츠 내 `@schema` 디렉티브 무시 |
| `allow_extra` | `False` | (`dumps` 전용) 스키마에 없는 추가 키 허용 |
| `exclude_schema` | `False` | (`dumps` 전용) 출력에서 `@schema` 줄 제외 |
| `extra_fields` | `ExtraFieldPolicy.ERROR` | 미선언 named arg 처리 정책 |

### ExtraFieldPolicy

```python
from fsonl import ExtraFieldPolicy

# 미선언 필드가 있으면 에러 (기본값)
result = fsonl.loads(text, schema=schema, extra_fields=ExtraFieldPolicy.ERROR)

# 미선언 필드 보존
result = fsonl.loads(text, schema=schema, extra_fields=ExtraFieldPolicy.PRESERVE)

# 미선언 필드 조용히 제거
result = fsonl.loads(text, schema=schema, extra_fields=ExtraFieldPolicy.STRIP)
```

### 에러

모든 에러에 줄 번호 포함: `str(error)`는 `"line 42: message"` 형태.

| 예외 | 종류 | 단계 |
|------|------|------|
| `ParseError` | `syntax_error` | 1단계 (문법 파싱) |
| `SchemaError` | `schema_error` | 스키마 정의 / 교차 검증 |
| `BindError` | `bind_error` | 2단계 (데이터와 스키마 불일치) |

모두 `FsonlError`를 상속하며, `FsonlError`는 `Exception`을 상속.

## 스키마 타입

```
string          -- JSON 문자열
number          -- JSON 숫자 (정수 또는 실수)
bool            -- true / false
null            -- null
any             -- 모든 JSON 값
string[]        -- 문자열 배열
(string | number)[]  -- 유니온 배열
{ cmd: string, id?: number }  -- 고정 구조 객체
string | null   -- nullable 문자열
```

## CLI

```bash
# 스키마 바인딩 파싱 (기본)
echo '@schema x(a: number)\nx(1)' | python -m fsonl parse

# Raw 파싱 (바인딩 없음)
echo 'x(1)' | python -m fsonl parse --raw

# 미정의 타입을 raw dict로
echo 'x(1)' | python -m fsonl parse --allow-unknown

# @schema 디렉티브만 추출
echo '@schema x(a: number)\nx(1)' | python -m fsonl parse --schema
```

## 포맷 개요

- 한 줄에 하나의 엔트리: `type(args)`
- 값은 JSON 리터럴: 문자열, 숫자, 불리언, null, 배열, 객체
- positional 인자가 named 인자보다 앞: `log("info", tag="v2")`
- 주석: `// ...` (인자 목록 바깥에서만)
- 파일 확장자: `.fsonl`, MIME: `text/fsonl`, 인코딩: UTF-8

## 스펙

- [SPEC.ko.md](https://github.com/fsonl/fsonl/blob/main/spec/SPEC.ko.md) -- 언어 스펙
- [GRAMMAR.ko.peg](https://github.com/fsonl/fsonl/blob/main/spec/GRAMMAR.ko.peg) -- PEG 형식 문법

## 라이선스

MIT
