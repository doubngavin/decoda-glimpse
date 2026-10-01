"""Golden set: 8 charts checked by hand on Jovian Archive (jovianarchive.com) on 01/10/2026.
All 26 activations (gate.line), type, authority and profile must match exactly.
Times are UTC as shown by Jovian. Run before every engine deploy: python3 test_golden.py"""
import engine
ORDER=["Sun","Earth","Moon","NorthNode","SouthNode","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]
G=[
("Nghi",(1996,9,5,7,45),"Generator","Sacral","2/4",
 "35.4 5.4 41.3 57.1 51.1 23.4 12.1 8.1 54.2 17.3 41.3 60.2 34.2","64.2 63.2 45.3 18.5 17.5 46.6 56.2 56.1 58.5 17.2 60.6 61.5 34.1"),
("Obama",(1961,8,5,5,24),"Projector","Emotional","6/2",
 "2.2 1.2 38.5 59.4 55.4 2.6 21.4 56.4 41.5 60.4 4.3 44.3 59.6","33.6 19.6 20.4 29.3 30.3 31.1 15.4 47.6 60.5 61.5 29.1 44.2 40.2"),
("Einstein",(1879,3,14,10,30),"Generator","Emotional","1/4",
 "11.4 12.4 46.3 41.3 31.3 38.3 10.1 14.1 41.6 36.5 59.5 27.6 8.1","36.1 6.1 5.4 41.1 31.1 25.6 51.2 60.1 30.4 17.1 59.2 24.1 8.1"),
("Diana",(1961,7,1,18,45),"Projector","Emotional","1/3",
 "21.3 48.3 57.2 40.1 37.1 63.6 42.6 39.5 41.1 60.3 4.4 44.4 40.1","39.1 38.1 30.1 29.4 30.4 15.6 23.6 59.2 41.4 60.2 4.5 44.2 40.1"),
("Madonna",(1958,8,16,12,5),"Generator","Sacral","5/1",
 "8.1 14.1 3.4 50.6 3.6 3.4 21.3 63.4 32.3 11.2 33.1 28.1 29.6","4.5 49.5 64.1 32.4 42.4 59.6 56.5 2.3 50.1 26.3 33.6 28.1 59.2"),
("Oprah",(1954,1,29,10,30),"Generator","Emotional","2/4",
 "44.4 24.4 18.4 60.2 56.2 34.1 57.6 46.4 12.4 50.6 62.3 32.4 29.1","19.2 33.2 34.5 61.4 62.4 49.1 19.2 43.6 35.6 44.2 53.6 32.6 4.6"),
("Swift",(1989,12,13,10,17),"Projector","Splenic","5/1",
 "6.1 36.1 17.1 30.2 29.2 18.6 28.3 6.6 52.5 58.4 10.4 38.1 44.6","26.5 45.5 15.4 13.6 7.6 58.6 60.6 14.3 52.5 38.5 58.1 38.2 1.4"),
("Sydney",(1975,6,22,13,10),"Manifesting Generator","Sacral","3/5",
 "25.5 46.5 33.4 34.3 20.3 37.6 27.3 13.3 25.4 39.3 50.6 5.1 18.5","15.3 10.3 5.6 34.1 20.1 35.4 7.3 42.4 51.6 53.5 50.3 9.5 18.3"),
]
bad=0
for name,(y,mo,d,h,mi),typ,auth,prof,ds,ps in G:
    hd=engine.compute(y,mo,d,h,mi,0,0,0)["hd"]
    mism=[]
    for tag,exp,got in (("D",ds.split(),hd["gates_design"]),("P",ps.split(),hd["gates_personality"])):
        for k,e in zip(ORDER,exp):
            g=got[k]
            if g!=e: mism.append(f"{tag}.{k} exp {e} got {g}")
    t=(hd["type"],hd["authority"],hd["profile"])
    ok = t==(typ,auth,prof) and not mism
    bad+= not ok
    print(("OK  " if ok else "FAIL"),name,t,"" if t==(typ,auth,prof) else f"expected {(typ,auth,prof)}",mism)
print("failures",bad)
assert bad == 0, "golden set failed: do NOT deploy"
