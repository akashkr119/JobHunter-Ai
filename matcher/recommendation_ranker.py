"""Composite recommendation scoring for JobHunter AI."""
from datetime import datetime,timezone

class RecommendationRanker:
    """Combine resume fit, target preferences, freshness and job state."""
    WEIGHTS={"resume":0.50,"preference":0.25,"freshness":0.10,"state":0.10,"lifecycle":0.05}

    @staticmethod
    def _bounded(value):
        try:return max(0.0,min(100.0,float(value)))
        except (TypeError,ValueError):return 0.0

    @staticmethod
    def freshness_score(value):
        if not value:return 0.0
        try:
            dt=datetime.fromisoformat(str(value).replace("Z","+00:00"));dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc);days=max(0.0,(datetime.now(timezone.utc)-dt).total_seconds()/86400)
        except (TypeError,ValueError):return 0.0
        return round(max(0.0,100.0-min(days,30.0)/30.0*100.0),1)

    @classmethod
    def score(cls,job):
        get=job.get if isinstance(job,dict) else lambda key,default=None:getattr(job,key,default)
        resume=cls._bounded(get("match_score",0));preference=cls._bounded(get("preference_score",100));freshness=cls.freshness_score(get("last_seen_at") or get("discovered_at"));status=str(get("application_status","new") or "new").lower();state={"new":100,"viewed":85,"applied":35,"interview":15,"offer":5,"rejected":0}.get(status,50);lifecycle=100.0 if bool(get("is_active",True)) else 0.0
        weighted={"resume":round(resume*cls.WEIGHTS["resume"],2),"preference":round(preference*cls.WEIGHTS["preference"],2),"freshness":round(freshness*cls.WEIGHTS["freshness"],2),"state":round(state*cls.WEIGHTS["state"],2),"lifecycle":round(lifecycle*cls.WEIGHTS["lifecycle"],2)};total=round(sum(weighted.values()),1)
        if not bool(get("preference_match",True)):total=min(total,39.9)
        label="top_pick" if total>=80 else "strong_match" if total>=65 else "good_match" if total>=50 else "consider"
        return {"recommendation_score":total,"recommendation_label":label,"recommendation_breakdown":{"weights":dict(cls.WEIGHTS),"raw":{"resume":resume,"preference":preference,"freshness":freshness,"state":float(state),"lifecycle":lifecycle},"weighted":weighted}}

    @classmethod
    def rank(cls,jobs):
        ranked=[]
        for job in jobs:
            row=dict(job) if isinstance(job,dict) else job
            if isinstance(row,dict):row.update(cls.score(row))
            ranked.append(row)
        return sorted(ranked,key=lambda x:(x.get("recommendation_score",0),x.get("match_score",0)),reverse=True)
