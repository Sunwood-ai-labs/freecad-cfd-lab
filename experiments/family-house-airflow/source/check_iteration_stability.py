"""Predeclared iteration-stability gates, not a mesh independence study."""
from pathlib import Path
import argparse,json,math
p=argparse.ArgumentParser();p.add_argument('--prior',required=True);p.add_argument('--final',required=True);p.add_argument('--output',required=True);a=p.parse_args()
prior=json.loads(Path(a.prior).read_text(encoding='utf-8'));final=json.loads(Path(a.final).read_text(encoding='utf-8'))
gap=final['source_iteration']-prior['source_iteration'];assert gap>=100
def compare(name,old,new,unit):
    assert math.isfinite(old)and math.isfinite(new)
    delta=abs(new-old);limit=max(.02*abs(new),.005)
    return {'name':name,'prior':old,'final':new,'unit':unit,'absolute_change':delta,'relative_change':delta/abs(new)if abs(new)>1e-15 else None,'allowed_absolute_change':limit,'pass':delta<=limit}
oldrooms={r['id']:r for r in prior['rooms']};newrooms={r['id']:r for r in final['rooms']}
rooms=[compare(key,oldrooms[key]['volume_weighted_mean_speed_m_s'],newrooms[key]['volume_weighted_mean_speed_m_s'],'m/s')for key in ['ldk','master','child1','child2']]
oldwins={r['id']:r for r in prior['windows']};newwins={r['id']:r for r in final['windows']}
windows=[compare(key+'/'+component,oldwins[key][component],newwins[key][component],'m3/s')for key in newwins for component in ['inward_reference_flux_m3_s','outward_reference_flux_m3_s']]
ok=all(r['pass']for r in rooms+windows)
result={'status':'pass'if ok else 'fail','prior_iteration':prior['source_iteration'],'final_iteration':final['source_iteration'],'iteration_gap':gap,
        'prior_U_sha256':prior['source_U_sha256'],'final_U_sha256':final['source_U_sha256'],
        'predeclared_gate':'4 main-room volume mean-speed change <= max(2%*|final|,0.005m/s); 9 windows each inward/outward reference flux change <= max(2%*|final|,0.005m3/s). Thresholds fixed before viewing the final comparison.',
        'room_speed_checks':rooms,'window_flux_checks':windows,
        'scope':'Iteration stability diagnostic on one mesh. Not a mesh independence study, experimental validation, uncertainty estimate or proof of real-house ventilation performance. Window-plane U interpolation is not the conservative mesh-face phi flux.'}
dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if ok else 1)
