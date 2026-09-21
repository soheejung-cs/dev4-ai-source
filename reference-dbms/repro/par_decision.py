import re
import pg8000.native as pg
con = pg.Connection(user='postgres', password='password', host='192.168.6.11',
                    port=5432, database='postgres', timeout=30)
def run(s): return [r[0] for r in con.run(s)]
def rows(s): return con.run(s)
def plan(q):
    con.run("SET geqo=off")
    return run("EXPLAIN "+q)
def top(q):
    p=plan(q); m=re.search(r'cost=[\d.]+\.\.([\d.]+)', p[0])
    par=[l for l in p if 'Workers Planned' in l]
    return float(m.group(1)), (int(par[0].split(':')[1]) if par else 0), p

Q=("SELECT count(*) FROM cast_info ci JOIN title t ON t.id=ci.movie_id "
   "WHERE ci.note LIKE '%(producer)%'")

print("=== 1) 병렬은 '규칙'이 아니라 '비용' 이다 — setup_cost 를 올리면 뒤집힌다 ===")
con.run("SET max_parallel_workers_per_gather=4")
for c in (1000, 100000, 300000, 400000, 410000, 500000):
    con.run("SET parallel_setup_cost=%d" % c)
    cost, w, _ = top(Q)
    print("  parallel_setup_cost=%-7d → 총비용 %12.2f   워커 %d  %s"
          % (c, cost, w, "병렬" if w else "직렬"))

print("\n=== 2) 워커 수는 비용탐색이 아니라 '테이블 크기' 휴리스틱 (log3 계단) ===")
con.run("SET parallel_setup_cost=1000")
for cap in (1,2,4,8,16):
    con.run("SET max_parallel_workers_per_gather=%d" % cap)
    _, w, _ = top(Q)
    print("  max_parallel_workers_per_gather=%-3d → Workers Planned %d" % (cap, w))
print("  (min_parallel_table_scan_size 8MB 에서 시작해 크기 3배마다 워커 +1, 상한은 GUC)")

print("\n=== 3) 비용을 워커 수로 그냥 나누지 않는다 — CPU 만 나누고 I/O 는 안 나눈다 ===")
for r in rows("SELECT relname, relpages, reltuples::bigint FROM pg_class "
              "WHERE relname IN ('cast_info','title')"):
    print("  %-10s relpages %8d  reltuples %12d" % (r[0], r[1], r[2]))
con.run("SET max_parallel_workers_per_gather=0")
_,_,ps = top(Q)
con.run("SET max_parallel_workers_per_gather=4")
_,_,pp = top(Q)
def pick(p, pat):
    for l in p:
        if pat in l: return l.strip()
print("  직렬 : "+pick(ps,'Seq Scan on cast_info'))
print("  병렬 : "+pick(pp,'Parallel Seq Scan on cast_info'))
print("  → 행수는 정확히 1/4 인데 비용은 1/4 이 아니다 (디스크 비용은 안 나눔)")
