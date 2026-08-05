"""Tests for target job preference evaluation."""
import pytest
from matcher.job_preferences import JobPreferences

def test_preferences_normalize_and_remove_duplicates():
    p=JobPreferences(target_titles=("QA Engineer"," qa engineer "),preferred_locations=("Bengaluru","BENGALURU"),work_modes=("Remote","remote"),desired_keywords=("Python","python"));assert p.target_titles==("qa engineer",);assert p.preferred_locations==("bengaluru",);assert p.work_modes==("remote",);assert p.desired_keywords==("python",)

def test_invalid_work_mode_rejected():
    with pytest.raises(ValueError,match="remote, hybrid or onsite"):JobPreferences(work_modes=("flexible",))

def test_matching_target_profile_scores_high():
    p=JobPreferences(target_titles=("qa automation engineer",),preferred_locations=("bengaluru",),work_modes=("hybrid",),desired_keywords=("python","selenium"));result=p.evaluate({"title":"Senior QA Automation Engineer","location":"Bengaluru","description":"Hybrid role using Python and Selenium"});assert result["preference_score"]==100.0;assert result["preference_match"] is True;assert result["matched_titles"]==["qa automation engineer"];assert result["matched_locations"]==["bengaluru"];assert result["matched_work_modes"]==["hybrid"];assert set(result["matched_keywords"])=={"python","selenium"}

def test_excluded_keyword_blocks_preference_match():
    p=JobPreferences(excluded_keywords=("manual testing",));result=p.evaluate({"title":"QA Engineer","description":"Mostly manual testing"});assert result["preference_match"] is False;assert result["excluded_keywords"]==["manual testing"]

def test_empty_preferences_accept_job():
    result=JobPreferences().evaluate({"title":"Anything"});assert result["preference_score"]==100.0;assert result["preference_match"] is True

def test_from_dict_and_to_dict_round_trip():
    data={"target_titles":["SDET"],"preferred_locations":["Pune"],"work_modes":["remote"],"desired_keywords":["pytest"],"excluded_keywords":["contract"]};assert JobPreferences.from_dict(data).to_dict()=={k:[str(x).lower() for x in v] for k,v in data.items()}
