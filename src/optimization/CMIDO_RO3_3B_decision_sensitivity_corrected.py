from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
PARETO=ROOT/'results'/'RO3'/'pareto'
OUT=ROOT/'results'/'RO3'/'decision_sensitivity'
NS=[1000,2500,5000]


def load(n,origin):
    tag=pd.Timestamp(origin).strftime('%Y%m%d')
    p=pd.read_csv(PARETO/f'RO3_pareto_N{n}_{tag}.csv')
    q=pd.read_csv(PARETO/f'RO3_pareto_N{n}_{tag}_decisions.csv')
    return p.sort_values('pareto_id').reset_index(drop=True),q


def norm_obj(a,b):
    x=a[['Z1','Z2','Z3']].to_numpy(float); y=b[['Z1','Z2','Z3']].to_numpy(float)
    den=np.maximum(np.maximum(np.abs(x),np.abs(y)),1.0)
    return float(np.mean(np.abs(x-y)/den)),float(np.max(np.abs(x-y)/den))


def matches(pa,pb):
    X=pa[['Z1','Z2','Z3']].to_numpy(float); Y=pb[['Z1','Z2','Z3']].to_numpy(float)
    scale=np.maximum(np.maximum(np.abs(X).max(0),np.abs(Y).max(0)),1.0)
    X=X/scale; Y=Y/scale
    used=set(); out=[]
    for i in range(len(X)):
        order=np.argsort(np.linalg.norm(Y-X[i],axis=1))
        j=next((k for k in order if k not in used),int(order[0]))
        used.add(j); out.append((i,j))
    return out


def qmetrics(qa,qb,ia,ib):
    keys=['material','month_ahead']
    a=qa[qa.pareto_id==ia].set_index(keys).q.astype(float)
    b=qb[qb.pareto_id==ib].set_index(keys).q.astype(float)
    idx=a.index.union(b.index)
    av=a.reindex(idx,fill_value=0).to_numpy(); bv=b.reindex(idx,fill_value=0).to_numpy()
    d=np.abs(av-bv)
    ta=float(np.abs(av).sum()); tb=float(np.abs(bv).sum())
    primary=float(d.sum()/max(ta,tb,1.0))
    zero_safe=float(np.mean(d/np.maximum(np.maximum(np.abs(av),np.abs(bv)),1.0)))
    return float(d.mean()),float(d.sum()),primary,float(d.max()),zero_safe,ta,tb


def main(origin):
    OUT.mkdir(parents=True,exist_ok=True)
    data={n:load(n,origin) for n in NS}
    rows=[]
    for na,nb in [(1000,2500),(2500,5000),(1000,5000)]:
        pa,qa=data[na]; pb,qb=data[nb]
        for ia,ib in matches(pa,pb):
            ra=pa.iloc[ia:ia+1]; rb=pb.iloc[ib:ib+1]
            mo,xo=norm_obj(ra,rb)
            mad,sad,agg,mx,zsafe,ta,tb=qmetrics(qa,qb,int(ra.pareto_id.iloc[0]),int(rb.pareto_id.iloc[0]))
            rows.append(dict(N_A=na,N_B=nb,pareto_id_A=int(ra.pareto_id.iloc[0]),pareto_id_B=int(rb.pareto_id.iloc[0]),mean_objective_distance=mo,max_objective_distance=xo,mean_abs_quantity_difference=mad,sum_abs_quantity_difference=sad,total_procurement_normalized_difference=agg,max_abs_quantity_difference=mx,mean_zero_safe_quantity_relative_difference=zsafe,total_procurement_A=ta,total_procurement_B=tb))
    df=pd.DataFrame(rows); tag=pd.Timestamp(origin).strftime('%Y%m%d')
    summary=df.groupby(['N_A','N_B'],as_index=False).agg(matched_solutions=('pareto_id_A','count'),mean_objective_distance=('mean_objective_distance','mean'),max_objective_distance=('max_objective_distance','max'),mean_abs_quantity_difference=('mean_abs_quantity_difference','mean'),mean_total_procurement_normalized_difference=('total_procurement_normalized_difference','mean'),max_total_procurement_normalized_difference=('total_procurement_normalized_difference','max'),mean_zero_safe_quantity_relative_difference=('mean_zero_safe_quantity_relative_difference','mean'))
    card=pd.DataFrame([{'N':n,'pareto_count':len(data[n][0]),'decision_rows':len(data[n][1])} for n in NS])
    df.to_csv(OUT/f'RO3_step33B_corrected_pairwise_{tag}.csv',index=False)
    summary.to_csv(OUT/f'RO3_step33B_corrected_summary_{tag}.csv',index=False)
    card.to_csv(OUT/f'RO3_step33B_corrected_cardinality_{tag}.csv',index=False)
    (OUT/f'RO3_step33B_corrected_manifest_{tag}.json').write_text(json.dumps({'origin':origin,'scenario_counts':NS,'optimizer_rerun':False,'primary_quantity_metric':'sum_abs_quantity_difference / max(total_procurement_A,total_procurement_B,1.0)','frontier_matching':'nearest normalized objective-space matching'},indent=2))
    print('='*78); print('RO3.3B CORRECTED DECISION-LEVEL SCENARIO SENSITIVITY'); print('='*78)
    print(card.to_string(index=False)); print('\nPairwise sensitivity:'); print(summary.to_string(index=False)); print('\nOutputs:',OUT)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--origin',required=True); main(ap.parse_args().origin)
