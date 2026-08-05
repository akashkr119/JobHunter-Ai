"""Tests for the unified recommendation ranking engine."""
from datetime import datetime,timedelta,timezone
from matcher.recommendation_ranker import RecommendationRanker

def recent(days=0):return (datetime.now(timezone.utc)-timedelta(days=days)).isoformat()

def test_perfect_new_active_job_is_top_pick():
    result=RecommendationRanker.score({"match_score":100,"preference_score":100,"preference_match":True,"last_seen_at":recent(),"application_status":"new","is_active":True});assert result["recommendation_score"]>=99;assert result["recommendation_label"]=="top_pick";assert set(result["recommendation_breakdown"]["weighted"])=={"resume","preference","freshness","state","lifecycle"}

def test_resume_match_has_largest_weight():
    high_resume=RecommendationRanker.score({"match_score":100,"preference_score":50,"last_seen_at":recent(),"application_status":"new","is_active":True});high_pref=RecommendationRanker.score({"match_score":50,"preference_score":100,"last_seen_at":recent(),"application_status":"new","is_active":True});assert high_resume["recommendation_score"]>high_pref["recommendation_score"]

def test_fresh_job_beats_old_equivalent_job():
    base={"match_score":80,"preference_score":80,"application_status":"new","is_active":True};fresh=RecommendationRanker.score({**base,"last_seen_at":recent(0)});old=RecommendationRanker.score({**base,"last_seen_at":recent(30)});assert fresh["recommendation_score"]>old["recommendation_score"]

def test_application_state_reduces_recommendation_after_apply():
    base={"match_score":85,"preference_score":90,"last_seen_at":recent(),"is_active":True};new=RecommendationRanker.score({**base,"application_status":"new"});applied=RecommendationRanker.score({**base,"application_status":"applied"});assert new["recommendation_score"]>applied["recommendation_score"]

def test_inactive_job_loses_lifecycle_points():
    base={"match_score":80,"preference_score":80,"last_seen_at":recent(),"application_status":"new"};active=RecommendationRanker.score({**base,"is_active":True});inactive=RecommendationRanker.score({**base,"is_active":False});assert active["recommendation_score"]-inactive["recommendation_score"]==5.0

def test_failed_preference_match_cannot_be_recommended_highly():
    result=RecommendationRanker.score({"match_score":100,"preference_score":100,"preference_match":False,"last_seen_at":recent(),"application_status":"new","is_active":True});assert result["recommendation_score"]==39.9;assert result["recommendation_label"]=="consider"

def test_rank_orders_best_recommendation_first():
    jobs=[{"id":1,"match_score":50,"preference_score":50,"last_seen_at":recent(20),"application_status":"viewed","is_active":True},{"id":2,"match_score":95,"preference_score":95,"last_seen_at":recent(),"application_status":"new","is_active":True}];ranked=RecommendationRanker.rank(jobs);assert [j["id"] for j in ranked]==[2,1];assert ranked[0]["recommendation_label"]=="top_pick"

def test_missing_or_invalid_date_is_safe():
    assert RecommendationRanker.freshness_score(None)==0.0;assert RecommendationRanker.freshness_score("bad-date")==0.0
