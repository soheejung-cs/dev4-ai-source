import re
import pg8000.native as pg
con = pg.Connection(user='postgres', password='password', host='192.168.6.11',
                    port=5432, database='postgres', timeout=60)
def run(s): return [r[0] for r in con.run(s)]
con.run("SET geqo=off"); con.run("SET join_collapse_limit=20"); con.run("SET from_collapse_limit=20")
con.run("SET max_parallel_workers_per_gather=0")

print("=== 1) 필터로 1행이 된 k 를 mk 와 조인 — PG 는 값-조건화를 하나? ===")
Q=("SELECT count(*) FROM keyword k JOIN movie_keyword mk ON mk.keyword_id=k.id "
   "WHERE k.keyword='character-name-in-title'")
for l in run("EXPLAIN ANALYZE "+Q):
    if 'movie_keyword' in l or 'keyword k' in l or 'Nested' in l or 'Hash Join' in l: print("  "+l.strip())

print("\n=== 2) 같은 조인을 **상수로** 주면? (값이 plan time 에 보인다) ===")
for l in run("EXPLAIN ANALYZE SELECT count(*) FROM movie_keyword WHERE keyword_id=117"):
    if 'movie_keyword' in l: print("  "+l.strip())

print("\n=== 3) 필터 없는 전체 조인 (eqjoinsel 이 답하는 질문) ===")
for l in run("EXPLAIN SELECT count(*) FROM keyword k JOIN movie_keyword mk ON mk.keyword_id=k.id"):
    if 'Join' in l or 'movie_keyword' in l: print("  "+l.strip())

print("\n=== 4) PG 가 mk.keyword_id 에 대해 들고 있는 통계 ===")
for r in con.run("SELECT n_distinct, array_length(most_common_vals::text::text[],1) AS n_mcv, "
                 "array_length(histogram_bounds::text::text[],1) AS n_hist "
                 "FROM pg_stats WHERE tablename='movie_keyword' AND attname='keyword_id'"):
    print("  n_distinct=%s  MCV개수=%s  히스토그램경계=%s" % tuple(r))
for r in con.run("SELECT (most_common_vals::text::int[])[1:5], (most_common_freqs)[1:5] "
                 "FROM pg_stats WHERE tablename='movie_keyword' AND attname='keyword_id'"):
    print("  상위 MCV=%s\n  상위 freq=%s" % tuple(r))
print("\n=== 5) keyword.id (PK) 쪽 통계 ===")
for r in con.run("SELECT n_distinct, most_common_vals IS NULL AS mcv_is_null "
                 "FROM pg_stats WHERE tablename='keyword' AND attname='id'"):
    print("  n_distinct=%s  MCV 없음=%s" % tuple(r))
