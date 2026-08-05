"""User target-profile preferences for filtering and ranking jobs."""
from dataclasses import dataclass,field
import re

@dataclass(frozen=True)
class JobPreferences:
    target_titles: tuple[str,...]=field(default_factory=tuple)
    preferred_locations: tuple[str,...]=field(default_factory=tuple)
    work_modes: tuple[str,...]=field(default_factory=tuple)
    desired_keywords: tuple[str,...]=field(default_factory=tuple)
    excluded_keywords: tuple[str,...]=field(default_factory=tuple)

    def __post_init__(self):
        modes=tuple(self._clean(x) for x in self.work_modes if self._clean(x))
        allowed={"remote","hybrid","onsite"}
        if any(x not in allowed for x in modes):raise ValueError("work_modes must contain only remote, hybrid or onsite")
        object.__setattr__(self,"target_titles",self._unique(self.target_titles));object.__setattr__(self,"preferred_locations",self._unique(self.preferred_locations));object.__setattr__(self,"work_modes",self._unique(modes));object.__setattr__(self,"desired_keywords",self._unique(self.desired_keywords));object.__setattr__(self,"excluded_keywords",self._unique(self.excluded_keywords))

    @staticmethod
    def _clean(value):return re.sub(r"\s+"," ",str(value or "").strip().lower())
    @classmethod
    def _unique(cls,values):return tuple(dict.fromkeys(cls._clean(x) for x in (values or ()) if cls._clean(x)))
    @classmethod
    def from_dict(cls,data):
        data=data or {};return cls(target_titles=tuple(data.get("target_titles") or ()),preferred_locations=tuple(data.get("preferred_locations") or ()),work_modes=tuple(data.get("work_modes") or ()),desired_keywords=tuple(data.get("desired_keywords") or ()),excluded_keywords=tuple(data.get("excluded_keywords") or ()))
    def to_dict(self):return {"target_titles":list(self.target_titles),"preferred_locations":list(self.preferred_locations),"work_modes":list(self.work_modes),"desired_keywords":list(self.desired_keywords),"excluded_keywords":list(self.excluded_keywords)}

    def evaluate(self,job):
        get=job.get if isinstance(job,dict) else lambda k,d="":getattr(job,k,d);title=self._clean(get("title",""));location=self._clean(get("location",""));description=self._clean(get("description",""));text=f"{title} {location} {description}";excluded=[x for x in self.excluded_keywords if x in text]
        title_matches=[x for x in self.target_titles if x in title or title in x];location_matches=[x for x in self.preferred_locations if x in location or location in x];keyword_matches=[x for x in self.desired_keywords if x in text]
        detected_modes=[]
        if "remote" in text:detected_modes.append("remote")
        if "hybrid" in text:detected_modes.append("hybrid")
        if any(x in text for x in ("on-site","onsite","on site","office based","office-based")):detected_modes.append("onsite")
        mode_match=not self.work_modes or bool(set(self.work_modes)&set(detected_modes))
        score=0.0;weights=0.0
        if self.target_titles:weights+=40;score+=40 if title_matches else 0
        if self.preferred_locations:weights+=25;score+=25 if location_matches else 0
        if self.work_modes:weights+=15;score+=15 if mode_match else 0
        if self.desired_keywords:weights+=20;score+=20*(len(keyword_matches)/len(self.desired_keywords))
        preference_score=round(score/weights*100,1) if weights else 100.0
        return {"preference_score":preference_score,"preference_match":not excluded and (preference_score>0 or weights==0),"matched_titles":title_matches,"matched_locations":location_matches,"matched_work_modes":sorted(set(detected_modes)&set(self.work_modes)),"matched_keywords":keyword_matches,"excluded_keywords":excluded}
