# 빌드·링크 구성 (모듈 횡단 — .52 실측, 최우선)

- libcubrid.so: -fvisibility=hidden/-fno-semantic-interposition/LTO 전무. JUMP_SLOT 14,788, 동적심볼 23,865 중 실사용 66. 같은 TU 안 호출도 PLT 경유 → 인라인/IPA/CSE 차단. 개별 최적화 다수의 근본 원인.
- TLS 전부 general-dynamic(DTPMOD64 32): cubthread::get_entry()가 __tls_get_addr 호출 하나. libcubrid는 dlopen 안 됨(검증) → -ftls-model=initial-exec 가능. 단 cubridsa/cs는 dlopen됨(util_support.c:86) — 금지.
- -Bsymbolic-functions 위험: libcubrid·libcascci 둘 다 OpenSSL 정적링크, 동일 심볼 ~5,711 익스포트. 현재 DT_NEEDED 순서로 libcubrid 승. 켜기 전 LD_DEBUG=bindings 확인 필수.
