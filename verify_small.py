# Independent re-computation of the small-class headline numbers.
# Cap base = undergraduate enrolment only, per the adopted motion.
# No imports from enrollment_lib or small_class_analysis. Raw csv -> answer.
import csv, math, re
FILES={'S22':'archive/S22.csv','S24':'archive/S24.csv',
       'S25':'Class Enrollment Summary by Term_Spring 25.csv',
       'S26':'Class Enrollment Summary by Term_Spring 26.csv',
       'F25':'Class Enrollment Summary by Term_Fall 25.csv',
       'F26':'Class Enrollment Summary_Fall 26.csv'}
SUP=re.compile(r"(reading\s*(and|&)\s*research|supervised\s+read|^research$|graduate\s+research"
               r"|research-related|dissertation|direction\s+of|directed\s+(writing|study|research)"
               r"|independent\s+(study|research|work)|experiential\s+study|general\s+examination"
               r"|thesis\s+research)",re.I)
def rows(p):
    with open(p,encoding='latin-1',newline='') as fh:
        rd=csv.reader(fh); hdr=None
        for r in rd:
            if not r: continue
            if hdr is None:
                if r[0] in ('Class Number','Course ID'): hdr=r
                continue
            if not r[0].strip().isdigit(): continue
            yield dict(zip(hdr,r))
def classes(t):
    out=[]
    for r in rows(FILES[t]):
        u=int(r['UGrad'] or 0); tot=int(r['Total'] or 0)
        # the cap counts UNDERGRADUATE enrolment only (motion item 3)
        n=u
        if u<1 or tot<1: continue
        nm=(r['Course Name'] or '')
        cat=(r['Course Title'] or '').split(None,1)
        num=re.search(r'(\d+)',cat[1]) if len(cat)>1 else None
        if SUP.search(nm): continue
        if num and int(num.group(1))==91: continue
        out.append((n,u))
    return out
def allowed(n): return min(math.floor(0.20*n+4),n)
print(f"{'term':>5} {'classes':>8} {'seats':>7} {'%cls n<=5':>10} {'%cls n=5':>9} {'%seats<12':>10} {'allowed%':>9} {'medsize':>8}")
for t in FILES:
    c=classes(t); seats=sum(u for _,u in c)
    le5=100*sum(1 for n,_ in c if n<=5)/len(c)
    eq5=100*sum(1 for n,_ in c if n==5)/len(c)
    s12=100*sum(u for n,u in c if n<12)/seats
    cap=100*sum(allowed(n)/n*u for n,u in c)/seats
    med=sorted(n for n,_ in c)[len(c)//2]
    print(f'{t:>5} {len(c):8d} {seats:7d} {le5:10.2f} {eq5:9.2f} {s12:10.2f} {cap:9.2f} {med:8d}')
print()
print('cap lookup:', {n:f'{100*allowed(n)/n:.0f}%' for n in (5,6,10,12,25,50,100,500)})
