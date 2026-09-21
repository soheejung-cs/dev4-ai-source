import re
import pg8000.native as pg
con = pg.Connection(user='postgres', password='password', host='192.168.6.11',
                    port=5432, database='postgres', timeout=30)
def run(s): return [r[0] for r in con.run(s)]
Q=("SELECT count(*) FROM cast_info ci JOIN title t ON t.id=ci.movie_id "
   "WHERE ci.note LIKE '%(producer)%'")
con.run("SET geqo=off"); con.run("SET max_parallel_workers_per_gather=4")
def par(S):
    con.run("SET parallel_setup_cost=%d" % S)
    p=run("EXPLAIN "+Q)
    return any('Workers Planned' in l for l in p), float(re.search(r'\.\.([\d.]+)',p[0]).group(1))

lo,hi=400000,410000
while hi-lo>1:
    mid=(lo+hi)//2
    (par(mid)[0] and (lo:=mid)) or (hi:=mid)
print("=== 병렬↔직렬이 뒤집히는 정확한 지점 ===")
print("  setup_cost %d → 병렬 / %d → 직렬" % (lo,hi))
SERIAL=837402.53; BASE=426897.05-1000
print("  직렬 총비용            %12.2f" % SERIAL)
print("  병렬 총비용(setup 제외) %12.2f" % BASE)
print("  단순 동점이라면 setup   %12.2f" % (SERIAL-BASE))
print("  실제 뒤집힌 곳          %12d" % hi)
print("  비율 (직렬/뒤집힘직전병렬) %.4f   ← add_path 의 STD_FUZZ_FACTOR = 1.01" 
      % (SERIAL/(BASE+lo)))

print("\n=== 워커 수 계산 검산 (compute_parallel_worker: 3배마다 +1) ===")
pages=252720; minp=1024  # min_parallel_table_scan_size 8MB / 8kB
w=0
while pages >= minp*(3**w): w+=1
print("  cast_info relpages %d (= %.0f MB), 8MB=%d pages" % (pages, pages*8/1024, minp))
for i in range(w+1):
    t=minp*(3**i)
    print("     워커 %d 문턱 %8d pages (%6.0f MB)  %s" % (i+1,t,t*8/1024,"통과" if pages>=t else "미달 → 멈춤"))
print("  → %d 워커. 실측 Workers Planned 6 과 일치" % w)

print("\n=== 비용 분해 검산 (CPU 만 나눈다) ===")
disk=252720*1.0
ser=705801.50; parc=365990.38
print("  디스크비용 = relpages x seq_page_cost = %10.2f" % disk)
print("  직렬 CPU   = %10.2f - %10.2f = %10.2f" % (ser,disk,ser-disk))
print("  병렬 예측  = %10.2f + %10.2f/4 = %10.2f" % (disk,ser-disk,disk+(ser-disk)/4))
print("  실측 병렬  = %10.2f   차이 %.2f" % (parc, abs(parc-(disk+(ser-disk)/4))))
