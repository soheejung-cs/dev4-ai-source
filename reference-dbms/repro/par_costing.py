import pg8000.native as pg
con = pg.Connection(user='postgres', password='password', host='192.168.6.11',
                    port=5432, database='postgres', timeout=20)
def run(sql):
    return [r[0] for r in con.run(sql)]

print("=== 버전 ===")
print(run("SELECT version()")[0][:60])

print("\n=== 병렬 관련 GUC (기본값) ===")
for g in ('max_parallel_workers_per_gather','parallel_setup_cost','parallel_tuple_cost',
          'min_parallel_table_scan_size','min_parallel_index_scan_size',
          'parallel_leader_participation','max_parallel_workers'):
    print("  %-32s %s" % (g, run("SHOW "+g)[0]))

Q = ("SELECT count(*) FROM cast_info ci JOIN title t ON t.id=ci.movie_id "
     "WHERE ci.note LIKE '%(producer)%'")

for label, setup in (("워커 4 허용", "SET max_parallel_workers_per_gather=4"),
                     ("병렬 금지",   "SET max_parallel_workers_per_gather=0")):
    con.run("SET geqo=off"); con.run(setup); con.run("SET parallel_setup_cost=1000")
    print("\n=== %s ===" % label)
    for l in run("EXPLAIN "+Q): print("  "+l)
