# Independent re-computation straight from the CSVs. No shared code with enrollment_lib.
import csv, collections
FILES={'F25':'Class Enrollment Summary by Term_Fall 25.csv','F26':'Class Enrollment Summary_Fall 26.csv',
       'S25':'Class Enrollment Summary by Term_Spring 25.csv','S26':'Class Enrollment Summary by Term_Spring 26.csv',
       'F24':'archive/F24.csv','F23':'archive/F23.csv','F22':'archive/F22.csv',
       'S24':'archive/S24.csv','S23':'archive/S23.csv','S22':'archive/S22.csv'}
def rows(p):
    with open(p,encoding='latin-1',newline='') as fh:
        rd=csv.reader(fh); hdr=None
        for r in rd:
            if not r: continue
            if hdr is None:
                if r and r[0] in ('Class Number','Course ID'): hdr=r
                continue
            if not r[0].strip().isdigit(): continue
            yield dict(zip(hdr,r))
ALIAS={'FRSEMR':'FYSEMR','HSEMR-EL':'FYSEMR','HSEMR-LE':'FYSEMR','AAAS':'AFRAMER','ECE':'ENG-SCI'}
D={}
for k,p in FILES.items():
    out=[]
    for r in rows(p):
        code=r['Course Title'].strip(); parts=code.split(None,1)
        subj=ALIAS.get(parts[0],parts[0]); cat=parts[1].strip() if len(parts)>1 else ''
        out.append((subj,cat,r['Course Department'].strip(),int(r['UGrad'] or 0),int(r['Total'] or 0),int(r['Withdraw'] or 0)))
    D[k]=out
print('rows per term:',{k:len(v) for k,v in D.items()})
print('ugrad totals:',{k:sum(x[3] for x in v) for k,v in D.items()})
def cd(k):
    a=collections.Counter()
    for s,c,dp,u,t,w in D[k]: a[s+' '+c]+=u
    return a
def matched(t0,t1):
    a,b=cd(t0),cd(t1); ks=[k for k in a if a[k]>0 and b.get(k,0)>0]; return a,b,ks
for t0,t1 in [('F25','F26'),('S25','S26')]:
    a,b,ks=matched(t0,t1)
    print(f'{t0}->{t1} matched courses={len(ks)} ugrad {sum(a[k] for k in ks)} -> {sum(b[k] for k in ks)}')
    cs=[k for k in ks if k.startswith('COMPSCI ')]
    print('   CS matched:',sum(a[k] for k in cs),'->',sum(b[k] for k in cs),
          f'{100*(sum(b[k] for k in cs)/sum(a[k] for k in cs)-1):+.1f}%')
    ge=[k for k in ks if k.startswith('GENED ')]
    print('   GenEd matched:',sum(a[k] for k in ge),'->',sum(b[k] for k in ge),
          f'{100*(sum(b[k] for k in ge)/sum(a[k] for k in ge)-1):+.1f}%')
# headline singles
for k in ['COMPSCI 50','COMPSCI 61','MATH 22A','MATH 55A','ECON 10A','STAT 110','STAT 104','PSY 1']:
    print(k, {t:cd(t).get(k,0) for t in ['F22','F23','F24','F25','F26']})
# CS dept share of ugrad by fall
for t in ['F22','F23','F24','F25','F26','S22','S23','S24','S25','S26']:
    tot=sum(x[3] for x in D[t]); cs=sum(x[3] for x in D[t] if x[2]=='Computer Science')
    ge=sum(x[3] for x in D[t] if x[0]=='GENED')
    print(t,'CS share %.2f'%(100*cs/tot),' GenEd share %.2f'%(100*ge/tot),' ugrad',tot)
# withdrawals spring
for t in ['S22','S23','S24','S25','S26']:
    print(t,'withdraw',sum(x[5] for x in D[t]),'per10k %.1f'%(10000*sum(x[5] for x in D[t])/sum(x[3] for x in D[t])))
