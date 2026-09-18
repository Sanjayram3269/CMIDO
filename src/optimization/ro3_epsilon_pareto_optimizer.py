from pathlib import Path
import argparse, json, time
import numpy as np
import pandas as pd
import pyomo.environ as pyo
ROOT=Path(__file__).resolve().parents[2]
SCEN_DIR=ROOT/'results'/'RO3'/'scenario_generation'; OUT=ROOT/'results'/'RO3'/'pareto'; OUT.mkdir(parents=True,exist_ok=True)
MATERIALS=['Cement','Granite','Ready Mixed Concrete','Steel Reinforcement Bars']; ALPHA=.95; H_MONTH=.025; DEFAULT_LEVELS=5; EPS_TOL=1e-7

def empirical_cvar(values,alpha=ALPHA):
    v=np.asarray(values,float)
    return float(min(eta+np.mean(np.maximum(v-eta,0))/(1-alpha) for eta in np.unique(v)))

def load_origin(n,origin):
    origin_ts=pd.Timestamp(origin); full=pd.read_csv(SCEN_DIR/f'RO3_step32_scenarios_{n}.csv'); full['forecast_origin']=pd.to_datetime(full['forecast_origin']); full['period']=pd.to_datetime(full['period']); frames=[]
    for mat in MATERIALS:
        df=full[(full.forecast_origin==origin_ts)&(full.material==mat)].copy()
        if df.empty: raise ValueError(f'No data for {mat}, {origin}, N={n}')
        frames.append(df)
    common=set(frames[0].scenario_id)
    for df in frames[1:]: common &= set(df.scenario_id)
    if len(common)!=n: raise ValueError(f'Expected {n} common scenarios; found {len(common)}')
    return frames

def prepare(frames):
    data={}; durations={}
    for df in frames:
        mat=df.material.iloc[0]; df=df.sort_values(['scenario_id','month_ahead'])
        for r in df.itertuples(): data[(mat,int(r.scenario_id),int(r.month_ahead))]=(float(r.demand),float(r.price))
        for r in df.drop_duplicates('scenario_id').itertuples(): durations[(mat,int(r.scenario_id))]=float(r.total_duration_days)
    periods=list(range(1,13)); scenarios=sorted(set(k[1] for k in data)); return data,durations,periods,scenarios

def arrival_coefficients(durations,periods,scenarios,origin):
    coeff={}
    for mat in MATERIALS:
        for w in scenarios:
            L=max(0.,durations[(mat,w)])
            for s in periods:
                arrival=origin+pd.DateOffset(months=s)+pd.to_timedelta(L,unit='D')
                for t in periods:
                    coeff[(mat,w,s,t)]=int(origin+pd.DateOffset(months=t)<=arrival<origin+pd.DateOffset(months=t+1))
    return coeff

def build_model(frames,objective,eps2=None,eps3=None):
    data,durations,periods,scenarios=prepare(frames); origin=pd.Timestamp(frames[0].forecast_origin.iloc[0]); avail=arrival_coefficients(durations,periods,scenarios,origin); m=pyo.ConcreteModel(); m.M=pyo.Set(initialize=MATERIALS); m.T=pyo.Set(initialize=periods); m.W=pyo.Set(initialize=scenarios)
    m.q=pyo.Var(m.M,m.T,domain=pyo.NonNegativeReals); m.I=pyo.Var(m.M,m.T,m.W,domain=pyo.NonNegativeReals); m.z=pyo.Var(m.M,m.T,m.W,domain=pyo.NonNegativeReals); m.eta=pyo.Var(domain=pyo.Reals); m.xi=pyo.Var(m.W,domain=pyo.NonNegativeReals)
    m.shortage_cap=pyo.Constraint(m.M,m.T,m.W,rule=lambda mm,mat,t,w:mm.z[mat,t,w]<=data[(mat,w,t)][0])
    def inventory(mm,mat,t,w):
        prev=0 if t==periods[0] else mm.I[mat,periods[t-2],w]; available=sum(avail[(mat,w,s,t)]*mm.q[mat,s] for s in periods); demand=data[(mat,w,t)][0]; return mm.I[mat,t,w]==prev+available-demand+mm.z[mat,t,w]
    m.inventory=pyo.Constraint(m.M,m.T,m.W,rule=inventory)
    m.cost=pyo.Expression(m.W,rule=lambda mm,w:sum(data[(mat,w,t)][1]*mm.q[mat,t]+H_MONTH*data[(mat,w,t)][1]*mm.I[mat,t,w] for mat in MATERIALS for t in periods))
    m.S=pyo.Expression(m.W,rule=lambda mm,w:sum(mm.z[mat,t,w] for mat in MATERIALS for t in periods)); m.cvar_link=pyo.Constraint(m.W,rule=lambda mm,w:mm.xi[w]>=mm.S[w]-mm.eta)
    m.Z1=pyo.Expression(expr=sum(m.cost[w] for w in scenarios)/len(scenarios)); m.Z2=pyo.Expression(expr=sum(m.S[w] for w in scenarios)/len(scenarios)); m.Z3=pyo.Expression(expr=m.eta+(1/(1-ALPHA))*sum(m.xi[w] for w in scenarios)/len(scenarios))
    if eps2 is not None:m.eps2=pyo.Constraint(expr=m.Z2<=float(eps2)+EPS_TOL)
    if eps3 is not None:m.eps3=pyo.Constraint(expr=m.Z3<=float(eps3)+EPS_TOL)
    m.obj=pyo.Objective(expr={'Z1':m.Z1,'Z2':m.Z2,'Z3':m.Z3}[objective],sense=pyo.minimize); return m

def reconstruct_shortage(frames,q,origin):
    data,durations,periods,scenarios=prepare(frames); origin=pd.Timestamp(origin); avail=arrival_coefficients(durations,periods,scenarios,origin); totals={w:0. for w in scenarios}
    for mat in MATERIALS:
        for w in scenarios:
            inv=0.
            for t in periods:
                available=sum(avail[(mat,w,s,t)]*q.get((mat,s),0.) for s in periods); d=data[(mat,w,t)][0]; net=inv+available; fulfilled=min(max(net,0.),d); totals[w]+=d-fulfilled; inv=net-fulfilled
    return np.asarray([totals[w] for w in scenarios],float)

def solve_model(frames,objective,eps2=None,eps3=None):
    model=build_model(frames,objective,eps2,eps3); solver=pyo.SolverFactory('highs'); t0=time.perf_counter(); result=solver.solve(model,tee=False); runtime=time.perf_counter()-t0; term=str(result.solver.termination_condition)
    if term!='optimal': return None,term,runtime
    q={(mat,t):float(pyo.value(model.q[mat,t])) for mat in MATERIALS for t in model.T}; shortages=reconstruct_shortage(frames,q,pd.Timestamp(frames[0].forecast_origin.iloc[0])); z3=empirical_cvar(shortages)
    if eps3 is not None and z3>float(eps3)+1e-5: raise RuntimeError(f'Independent CVaR exceeds eps3: {z3} > {eps3}')
    vals={'Z1':float(pyo.value(model.Z1)),'Z2':float(pyo.value(model.Z2)),'Z3':z3,'runtime_sec':runtime,'q':q,'epigraph_Z3':float(pyo.value(model.Z3))}; return vals,term,runtime

def dominates(a,b,tol=1e-7): return a['Z1']<=b['Z1']+tol and a['Z2']<=b['Z2']+tol and a['Z3']<=b['Z3']+tol and (a['Z1']<b['Z1']-tol or a['Z2']<b['Z2']-tol or a['Z3']<b['Z3']-tol)
def pareto_filter(records):
    unique={tuple(round(r[k],8) for k in ('Z1','Z2','Z3')):r for r in records}; vals=list(unique.values()); return sorted([a for i,a in enumerate(vals) if not any(j!=i and dominates(b,a) for j,b in enumerate(vals))],key=lambda x:(x['Z1'],x['Z2'],x['Z3']))

def run(n,origin,levels=DEFAULT_LEVELS):
    frames=load_origin(n,origin); anchors={}
    for obj in ['Z1','Z2','Z3']:
        vals,term,rt=solve_model(frames,obj)
        if vals is None: raise RuntimeError(f'Anchor {obj} failed: {term}')
        anchors[obj]=vals
    lower2=min(v['Z2'] for v in anchors.values()); upper2=anchors['Z1']['Z2']; lower3=min(v['Z3'] for v in anchors.values()); upper3=anchors['Z1']['Z3']; records=[]
    for a in np.linspace(lower2,upper2,levels):
        for b in np.linspace(lower3,upper3,levels):
            vals,term,rt=solve_model(frames,'Z1',float(a),float(b))
            if vals is not None: vals.update(eps2=float(a),eps3=float(b),termination=term); records.append(vals)
    pareto=pareto_filter(records); tag=pd.Timestamp(origin).strftime('%Y%m%d'); stem=f'RO3_pareto_N{n}_{tag}'
    pd.DataFrame([{k:r[k] for k in ['Z1','Z2','Z3','eps2','eps3','runtime_sec']}|{'pareto_id':i,'scenario_count':n,'forecast_origin':origin} for i,r in enumerate(pareto,1)]).to_csv(OUT/f'{stem}.csv',index=False)
    qrows=[{'pareto_id':i,'material':mat,'month_ahead':t,'q':q} for i,r in enumerate(pareto,1) for (mat,t),q in r['q'].items()]; pd.DataFrame(qrows).to_csv(OUT/f'{stem}_decisions.csv',index=False)
    manifest={'scenario_count':n,'forecast_origin':origin,'epsilon_levels':levels,'anchors':{k:{x:v[x] for x in ['Z1','Z2','Z3']} for k,v in anchors.items()},'epsilon_bounds':{'Z2':[float(lower2),float(upper2)],'Z3':[float(lower3),float(upper3)]},'feasible_epsilon_solves':len(records),'pareto_count':len(pareto),'alpha':ALPHA,'monthly_holding_rate':H_MONTH,'solver':'HiGHS','model':'CMIDO_RO3_4_4_v1.1_corrected_cvar_reporting'}
    (OUT/f'{stem}_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8'); print('RO3 PRODUCTION PARETO RUN — CORRECTED CVaR REPORTING'); print(f'Origin: {origin} | N={n} | epsilon grid={levels}x{levels}'); print(f"Anchor Z1={anchors['Z1']['Z1']:.6f}, Z2={anchors['Z1']['Z2']:.6f}, Z3={anchors['Z1']['Z3']:.6f}"); print(f'Feasible epsilon solves: {len(records)}'); print(f'Computed nondominated solutions: {len(pareto)}'); print(f'Pareto file: {OUT/f"{stem}.csv"}')
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--n',type=int,choices=[100,250,500,1000,2500,5000],required=True); ap.add_argument('--origin',required=True); ap.add_argument('--epsilon-levels',type=int,default=5); a=ap.parse_args(); run(a.n,a.origin,a.epsilon_levels)
