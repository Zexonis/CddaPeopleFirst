"""Generates mods/PeopleFirst/keep/*.json: v0.6 "The Keep", pass 1: who decides (concept section 14).

The town meeting (weekly, at home in the evening), the chief it elects from everyone's own views, quarrels brought to
the meeting and settled by the chief (you, if they chose you), dissent and the vote of confidence, and what happens when
the chief dies or disappears.  An NPC chief also decides who may move in.

Usage:  python tools/gen_keep.py mods/PeopleFirst
"""
import json, os, sys

ROOT = sys.argv[1]
OUT = os.path.join(ROOT, "keep")
os.makedirs(OUT, exist_ok=True)

def m(e): return {"math": [e]}
def g(n): return {"global_val": n}
def ctx(n): return {"context_val": n}
def eoc(id_, effect, comment=None, condition=None, **extra):
    o = {"type": "effect_on_condition", "id": id_}
    if comment: o["//"] = comment
    o.update(extra)
    if condition: o["condition"] = condition
    o["effect"] = effect
    return o
def say(text, t="info"): return {"u_message": text, "type": t}
def name_into(gvar, tag="<u_name>"): return {"set_string_var": tag, "target_var": g(gvar), "parse_tags": True}
def line(key): return {"run_eocs": "PF_SAY_keep", "alpha_talker": "avatar", "variables": {"line": key}}
def pool(prefix, n):
    """Effects: one random line of prefix_0..n-1, never the same twice running."""
    return [m(f"_p = rand({n - 1})"), {"if": m(f"_p == value_or(pf_kl_{prefix}, -1)"), "then": [m(f"_p = (_p + 1) % {n}")]}, m(f"pf_kl_{prefix} = _p")] + \
           [{"if": m(f"_p == {i}"), "then": [line(f"{prefix}_{i}")]} for i in range(n)]
CALM = "value_or(pf_set_chatter, 1) == 1"
AT_HOME = "value_or(pf_home_set, 0) == 1"
TODAY = "floor(time('now') / time('1 d'))"
HOUR = "time_since('midnight', 'unit': 'hours')"
ADULT = {"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18")]}
ADULT_RES = {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), m("has_var(u_pf_uid)")]}
IS_CHIEF = {"and": [m("value_or(pf_chief_set, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_chief_uid")]}]}
# pass 6: the council.  A councillor carries the current term's number; the speaker (seat 1) is also the chief.
IS_COUNCIL = m("(value_or(pf_cn_n, 0) > 0) * (value_or(u_pf_cn_term, -1) == value_or(pf_cn_term, -2))")
COUNCIL_ON = "(value_or(pf_law_council, 0) == 1) * (value_or(pf_cn_n, 0) >= 2)"
MEET_DAY = 2          # TODAY % 7: the weekly meeting (market day is 6)
MIN_ADULTS = 4        # grown-ups who live here before the place holds meetings
by_uid = lambda eocs, uid: {"u_run_npc_eocs": eocs, "unique_ids": [uid], "local": False}
files = {}


def days_txt(src, dst):
    """Effects: dst = "less than a day" / "a day" / "N days" for the day count in src (playtest 3: "1 days now")."""
    return [{"set_string_var": "<global_val:%s> days" % src, "target_var": g(dst), "parse_tags": True},
            {"if": m(f"{src} == 1"), "then": [{"set_string_var": "a day", "target_var": g(dst)}]},
            {"if": m(f"{src} < 1"), "then": [{"set_string_var": "less than a day", "target_var": g(dst)}]}]

# ============================================================ THE MEETING
files["meeting.json"] = [
    eoc("PF_KEEP_tick", [
        {"if": m(f"value_or(pf_mt_stday, -1) != {TODAY}"), "then": [m("pf_mt_state = 0")]},
        {"if": {"and": [m(f"{HOUR} >= 19"), m(f"{HOUR} < 22"), m(f"value_or(pf_mt_day, -1) != {TODAY}"),
                        m(f"({TODAY} % 7 == {MEET_DAY}) + value_or(pf_mt_due, 0) + (value_or(pf_meetings_total, 0) == 0) > 0")]}, "then": [
            {"u_location_variable": g("pf_kp_av")},
            {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [
                {"if": m("value_or(pf_mt_state, 0) == 0"), "then": [
                    {"run_eocs": "PF_KEEP_count"},
                    {"if": m(f"pf_kp_n >= {MIN_ADULTS}"), "then": [
                        m("pf_mt_small_said = 0"),
                        {"run_eocs": "PF_THREAT_scan"},
                        {"if": m("pf_threat == 0"), "then": [{"run_eocs": "PF_KEEP_call"}]}], "else": [
                        # full run day 124: after the deaths, meeting night just stopped coming and nothing said why
                        {"if": m("(value_or(pf_meetings_total, 0) > 0) * (value_or(pf_mt_small_said, 0) == 0)"), "then": [
                            m("pf_mt_small_said = 1"), m(f"pf_mt_day = {TODAY}"), m("pf_mt_due = 0"), line("meet_too_few")]}]}],
                 "else": [{"if": m("time('now') - pf_mt_t >= time('20 m')"), "then": [{"run_eocs": "PF_KEEP_agenda"}]}]}]}]},
    ], "Every 10 minutes at home: on meeting day (one evening a week, or the next evening after the chief is lost, or the very first time the place has 4+ grown-ups living here), between 19:00 and 22:00 when you're home and it's calm, the meeting is called; 20 minutes later it sits.",
        recurrence="10 minutes", **{"global": True}, condition=m(AT_HOME)),
    eoc("PF_KEEP_count", [
        m("pf_kp_n = 0"),
        {"u_run_npc_eocs": [{"id": "PF_KEEP_count_one", "condition": ADULT_RES, "effect": [m("pf_kp_n += 1")]}], "local": True, "npc_range": 60},
    ], "u = avatar.  pf_kp_n = grown-ups who live here, in the bubble."),
    eoc("PF_KEEP_call", [
        m("pf_mt_state = 1"), m("pf_mt_t = time('now')"), m(f"pf_mt_stday = {TODAY}"),
        {"u_run_npc_eocs": [{"id": "PF_KEEP_gather", "condition": {"and": [ADULT_RES, {"not": {"u_has_effect": "sleep"}}]}, "effect": [
            {"copy_var": g("pf_home_loc"), "target_var": {"u_val": "pf_walk_to"}},
            {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("rand(6) - 3"), "y_adjust": m("rand(6) - 3")},
            {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]}], "local": True, "npc_range": 60},
        {"if": m(CALM), "then": [{"if": m("value_or(pf_meetings_total, 0) == 0"), "then": [line("call_first")], "else": pool("call", 3)}]},
    ], "u = avatar.  Somebody bangs a pot: everyone who lives here walks over."),
    eoc("PF_KEEP_agenda", [
        m("pf_mt_state = 0"), m(f"pf_mt_day = {TODAY}"), m("pf_mt_due = 0"),
        m("pf_meetings_total = value_or(pf_meetings_total, 0) + 1"),
        {"if": m("value_or(pf_town_named, 0) == 1"), "then": [{"copy_var": g("pf_town_name"), "target_var": g("pf_kp_place")}],
         "else": [{"set_string_var": "the place", "target_var": g("pf_kp_place")}]},
        {"u_location_variable": g("pf_kp_av")},
        m("pf_kp_elect = value_or(pf_chief_set, 0) == 0"), m("pf_kp_judge = 0"),
        # is the chief here?
        {"if": m("value_or(pf_chief_set, 0) == 1"), "then": [
            {"copy_var": g("pf_chief_uid"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
            {"if": m("pf_find_ok == 1"), "then": [m("pf_chief_away = 0"), m("pf_kp_judge = 1"), {"copy_var": g("pf_find_who"), "target_var": g("pf_kp_chief_t")}],
             "else": [m("pf_chief_away = value_or(pf_chief_away, 0) + 1"),
                      {"if": m("pf_chief_away >= 2"), "then": [line("chief_gone"),
                                                                {"if": m("value_or(pf_law_lord, 0) == 1"), "then": [{"run_eocs": "PF_KEEP_succession"}],
                                                                 "else": [m("pf_chief_set = 0"), m("pf_kp_elect = 1")]}],
                       "else": [line("chief_absent")]}]}]},
        {"if": m("value_or(pf_chief_set, 0) == 2"), "then": [m("pf_kp_judge = 2")]},
        # the council (pass 6): chosen when the law is new or a seat is lost, and again every four weeks
        m("pf_kp_council = 0"),
        {"if": m("(value_or(pf_law_council, 0) == 1) * (pf_kp_elect == 0)"), "then": [
            {"if": m("value_or(pf_cn_n, 0) < 2"), "then": [m("pf_kp_elect = 1")],
             "else": [{"if": m("time('now') - value_or(pf_cn_since, 0) >= time('28 d')"), "then": [m("pf_kp_elect = 1"), line("council_term")],
                       "else": [{"run_eocs": "PF_KEEP_cn_present"}, {"if": m("pf_cnv_here > 0"), "then": [m("pf_kp_council = 1")]}]}]}]},
        {"if": m("value_or(pf_meetings_total, 0) == 1"), "then": [line("first")], "else": [{"if": m(CALM), "then": pool("open", 3)}]},
        # dissent: a vote of confidence when more than half of them have turned on the chief
        {"if": m("(pf_kp_elect == 0) * (value_or(pf_chief_set, 0) > 0)"), "then": [
            {"run_eocs": "PF_KEEP_dissent"},
            {"if": m("value_or(pf_law_lord, 0) == 1"),
             "then": [{"if": m("(pf_kd_n >= 2) * (pf_kd_dis * 3 > pf_kd_n * 2)"), "then": [m("pf_kp_old_set = value_or(pf_chief_set, 0)"), {"copy_var": g("pf_chief_name"), "target_var": g("pf_kp_old_name")}, {"copy_var": g("pf_chief_uid"), "target_var": g("pf_kp_old_uid")}, line("coup"), m("pf_law_lord = 0"), m("pf_kp_elect = 1"), m("pf_kp_conf = 1"),
                                                                                        m("pf_coups_total = value_or(pf_coups_total, 0) + 1")]}],
             "else": [{"if": m("(pf_kd_n >= 2) * (pf_kd_dis * 2 > pf_kd_n)"), "then": [m("pf_kp_old_set = value_or(pf_chief_set, 0)"), {"copy_var": g("pf_chief_name"), "target_var": g("pf_kp_old_name")}, {"copy_var": g("pf_chief_uid"), "target_var": g("pf_kp_old_uid")}, line("confidence"), m("pf_kp_elect = 1"), m("pf_kp_conf = 1"),
                                                                                      m("pf_confidence_total = value_or(pf_confidence_total, 0) + 1")]}]}]},
        m("pf_kp_events = 0"),
        {"if": m("pf_kp_elect == 1"), "then": [{"if": m("value_or(pf_law_council, 0) == 1"), "then": [{"run_eocs": "PF_KEEP_council_election"}],
                                               "else": [{"run_eocs": "PF_KEEP_election"}]},
                                              # KinfoldLab: Mitzi, who had held the place alone, was voted out and said nothing at all
                                              {"if": m("pf_kp_conf == 1"), "then": [{"run_eocs": "PF_KEEP_deposed"}]}],
         "else": [{"run_eocs": "PF_KEEP_tithe_step"},
                  {"if": m("pf_kp_judge + pf_kp_council > 0"), "then": [
                      {"run_eocs": "PF_KEEP_dispute_scan"},
                      {"if": m("pf_kd_found == 1"), "then": [m("pf_kp_events += 1"), {"run_eocs": "PF_KEEP_dispute"}]}]},
                  {"run_eocs": "PF_KEEP_exile_step"},
                  {"if": m("(pf_kp_judge == 1) * value_or(pf_law_lord, 0)"), "then": [{"run_eocs": "PF_KEEP_heir_step"}]},
                  {"run_eocs": "PF_KEEP_law_step"},
                  {"if": m(f"(pf_kp_events == 0) * ({CALM})"), "then": pool("quiet", 4)}]},
        m("pf_kp_conf = 0"),
    ], "u = avatar.  The meeting sits.  First: is there a chief, and are they here (away from two meetings running, the chair is empty)?  If there's no chief, or more than half have turned on them, a vote.  Otherwise: the week's tithe (and anyone who kept their share back), the worst quarrel in the place for the chief to settle, and a law put to the vote (yours, or someone's who has a reason).  If none of that comes up, it's a quiet one."),
    eoc("PF_KEEP_deposed", [
        {"if": m("pf_kp_old_set == 2"),
         "then": [{"if": m("value_or(pf_chief_set, 0) == 2"), "then": [line("deposed_kept_you")], "else": [line("deposed_you")]}],
         "else": [{"if": {"and": [m("value_or(pf_chief_set, 0) == 1"), {"compare_string": [g("pf_chief_uid"), g("pf_kp_old_uid")]}]},
                   "then": [line("deposed_kept")],
                   "else": [line("deposed"),
                            # it stings: the old chief thinks less of whoever took the chair
                            {"if": m("value_or(pf_chief_set, 0) == 2"), "then": [{"set_string_var": "AVATAR", "target_var": g("pf_m_other")}],
                             "else": [{"copy_var": g("pf_chief_uid"), "target_var": g("pf_m_other")}]},
                            {"u_run_npc_eocs": [{"id": "PF_KEEP_deposed_sting", "condition": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kp_old_uid")]},
                                                 "effect": [m("pf_mv_role = 1"), m("pf_m_str_in = 40"), {"run_eocs": "PF_MV_ruled_against"}]}],
                             "local": True, "npc_range": 60}]}]},
    ], "u = avatar.  After a vote of confidence or a coup: how the one who lost the chair takes it (an NPC who lost it holds it against whoever won)."),
    eoc("PF_KEEP_dissent", [
        m("pf_kd_dis = 0"), m("pf_kd_n = 0"),
        {"if": m("pf_chief_set == 2"), "then": [{"set_string_var": "AVATAR", "target_var": g("pf_m_other")}], "else": [{"copy_var": g("pf_chief_uid"), "target_var": g("pf_m_other")}]},
        {"u_run_npc_eocs": [{"id": "PF_KEEP_dissent_one", "condition": {"and": [ADULT_RES, {"not": IS_CHIEF}]}, "effect": [
            {"run_eocs": "PF_VIEW_read"}, m("pf_kd_n += 1"),
            {"if": m("(pf_read_t < 5) * (pf_read_x >= 40) + (pf_read_w < -10) > 0"), "then": [m("pf_kd_dis += 1")]}]}], "local": True, "npc_range": 60},
    ], "u = avatar.  Everyone who lives here judges the chief from their own view: trust under 5 with tension 40+, or warmth below -10, is dissent."),
]

# ============================================================ THE VOTE
files["election.json"] = [
    eoc("PF_KEEP_election", [
        m("pf_ke_you = 0"), m("pf_ke_total = 0"), m("pf_kw_best = 0"), m("pf_kw_sel = 0"),
        {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [
            {"if": {"u_query": "The meeting is choosing who leads the place.  Will you stand?", "default": False}, "then": [m("pf_ke_you = 1")]}]},
        m("pf_kv_AVATAR = 0"),
        {"u_run_npc_eocs": [{"id": "PF_KEEP_tally_reset", "condition": ADULT_RES, "effect": [
            {"set_string_var": "pf_kv_<u_val:pf_uid>", "target_var": ctx("kv"), "parse_tags": True}, m("v_kv = 0")]}], "local": True, "npc_range": 60},
        {"u_run_npc_eocs": ["PF_KEEP_voter"], "local": True, "npc_range": 60},
        {"u_run_npc_eocs": [{"id": "PF_KEEP_count_votes", "condition": ADULT_RES, "effect": [
            {"set_string_var": "pf_kv_<u_val:pf_uid>", "target_var": ctx("kv"), "parse_tags": True},
            {"if": m("value_or(v_kv, 0) > pf_kw_best"), "then": [m("pf_kw_best = v_kv"), m("pf_kw_sel = 1"),
                                                                  {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kw_uid")}, name_into("pf_kw_name")]}]}],
         "local": True, "npc_range": 60},
        {"if": m("(pf_ke_you == 1) * (pf_kv_AVATAR > pf_kw_best)"), "then": [m("pf_kw_best = pf_kv_AVATAR"), m("pf_kw_sel = 2")]},
        {"if": m("(pf_kw_sel > 0) * (pf_kw_best * 3 < pf_ke_total)"), "then": [m("pf_kw_sel = 0")]},
        {"if": m("pf_kw_sel == 0"), "then": [line("no_chief")], "else": [
            m("pf_kw_again = (pf_kw_sel == value_or(pf_chief_set, 0)) * ((pf_kw_sel == 2) + 0)"),
            {"if": m("(pf_kw_sel == 1) * (value_or(pf_chief_set, 0) == 1)"), "then": [
                {"if": {"compare_string": [g("pf_kw_uid"), g("pf_chief_uid")]}, "then": [m("pf_kw_again = 1")]}]},
            {"if": m("pf_kw_sel == 1"), "then": [m("pf_chief_set = 1"), {"copy_var": g("pf_kw_uid"), "target_var": g("pf_chief_uid")}, {"copy_var": g("pf_kw_name"), "target_var": g("pf_chief_name")}],
             "else": [m("pf_chief_set = 2"), {"set_string_var": "AVATAR", "target_var": g("pf_chief_uid")}, {"set_string_var": "you", "target_var": g("pf_chief_name")}]},
            m("pf_chief_away = 0"), m("pf_elections_total = value_or(pf_elections_total, 0) + 1"),
            {"if": m("pf_kw_again == 0"), "then": [m("pf_chief_since = time('now')")]},
            {"if": m("pf_kw_sel == 2"),
             "then": [{"if": m("pf_kw_again == 1"), "then": [line("kept_you")], "else": [line("elected_you")]}],
             "else": [{"if": m("pf_kw_again == 1"), "then": [line("kept")], "else": pool("elected", 2)}]}]},
    ], "u = avatar.  You're asked whether you'll stand (if you're at the meeting).  Every grown-up who lives here votes, from their own view (trust + warmth / 2 - tension), for the one they'd follow: anyone else who lives here, or you if you stood.  Only people they actually know count (warmth + trust 10+); a stranger, with no grudges against them, would otherwise beat everyone who has lived together long enough to argue.  Knowing nobody, they abstain.  Most votes wins, if it's at least a third of the voters (else nobody is chosen); a tie goes to whoever was counted first, and you have to beat them outright."),
    eoc("PF_KEEP_voter", [
        {"u_set_talker": g("pf_kv_voter")}, {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kv_vuid")},
        m("pf_kv_best = -999"), m("pf_kv_sel = 0"),
        {"if": m("pf_ke_you == 1"), "then": [
            {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
            {"if": m("pf_read_t + pf_read_w >= 10"), "then": [m("pf_kv_best = pf_read_t + pf_read_w / 2 - pf_read_x"), m("pf_kv_sel = 2")]}]},
        {"u_run_npc_eocs": [{"id": "PF_KEEP_cand", "condition": {"and": [ADULT_RES, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kv_vuid")]}}]}, "effect": [
            {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_m_other")},
            {"run_eocs": "PF_VIEW_read", "alpha_talker": g("pf_kv_voter")},
            m("_s = pf_read_t + pf_read_w / 2 - pf_read_x"),
            {"if": m("(_s > pf_kv_best) * (pf_read_t + pf_read_w >= 10)"), "then": [m("pf_kv_best = _s"), m("pf_kv_sel = 1"),
                                                   {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kv_buid")}, {"u_set_talker": g("pf_kv_bt")}]}]}],
         "local": True, "npc_range": 60},
        {"if": m("pf_kv_sel == 2"), "then": [m("pf_kv_AVATAR += 1"), m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_voted_for", "beta_talker": "avatar"}]},
        {"if": m("pf_kv_sel == 1"), "then": [
            {"set_string_var": "pf_kv_<global_val:pf_kv_buid>", "target_var": ctx("kv"), "parse_tags": True}, m("v_kv = value_or(v_kv, 0) + 1"),
            m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_voted_for", "beta_talker": g("pf_kv_bt")}]},
        m("pf_ke_total += 1"),
    ], "u = a grown-up who lives here: their vote (a voted_for moment with the one they chose).", condition=ADULT_RES),
]

# ============================================================ QUARRELS
TOPICS = ["who's been taking more than their share from the stores", "a borrowed tool that came back broken", "whose turn it really was on the watch",
          "the noise at night", "what to do with the dead, and how far from the houses", "a promise made on the road and never kept"]
topic = [m(f"_t = rand({len(TOPICS) - 1})")] + [{"if": m(f"_t == {i}"), "then": [{"set_string_var": t, "target_var": g("pf_kd_topic")}]} for i, t in enumerate(TOPICS)] + [
    {"if": m("(pf_kd_arole == 1) + (pf_kd_brole == 1) > 0"), "then": [{"if": m("rand(1) == 0"), "then": [{"set_string_var": "the cooking, and who keeps burning it", "target_var": g("pf_kd_topic")}]}]},
    {"if": m("(pf_kd_ahh > 0) * (pf_kd_ahh == pf_kd_bhh)"), "then": [{"set_string_var": "a family matter that should have stayed in the family", "target_var": g("pf_kd_topic")}]}]
def outcome(winner, loser, chief):
    return [{"run_eocs": "PF_MK_ruled_for", "alpha_talker": chief, "beta_talker": g(f"pf_kd_{winner}")},
            {"run_eocs": "PF_MK_ruled_against", "alpha_talker": chief, "beta_talker": g(f"pf_kd_{loser}")},
            m("pf_m_str_in = 20"), {"run_eocs": "PF_MK_made_peace", "alpha_talker": g("pf_kd_a"), "beta_talker": g("pf_kd_b")},
            {"copy_var": g(f"pf_kd_{winner}name"), "target_var": g("pf_kd_wname")}, {"copy_var": g(f"pf_kd_{loser}name"), "target_var": g("pf_kd_lname")}]
SPLIT = lambda: [m("pf_m_str_in = 45"), {"run_eocs": "PF_MK_made_peace", "alpha_talker": g("pf_kd_a"), "beta_talker": g("pf_kd_b")}]
# the pair settled at the last meeting with a quarrel doesn't come up again for 4 weeks (u = B, pf_kd_tauid = A)
SETTLED = {"and": [m("time('now') - value_or(pf_kd_last_t, -999999) < time('28 d')"),
                   {"or": [{"and": [{"compare_string": [g("pf_kd_tauid"), g("pf_kd_last_a")]}, {"compare_string": [{"u_val": "pf_uid"}, g("pf_kd_last_b")]}]},
                           {"and": [{"compare_string": [g("pf_kd_tauid"), g("pf_kd_last_b")]}, {"compare_string": [{"u_val": "pf_uid"}, g("pf_kd_last_a")]}]}]}]}
files["quarrel.json"] = [
    eoc("PF_KEEP_dispute_scan", [
        m("pf_kd_found = 0"), m("pf_kd_best = 34"),
        {"u_run_npc_eocs": [{"id": "PF_KEEP_ds_a", "condition": {"and": [ADULT_RES, {"not": IS_CHIEF}]}, "effect": [
            {"u_set_talker": g("pf_kd_ta")}, {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kd_tauid")}, name_into("pf_kd_taname"),
            m("pf_kd_tarole = value_or(u_pf_role, 0)"), m("pf_kd_tahh = value_or(u_pf_household, 0)"),
            {"u_run_npc_eocs": [{"id": "PF_KEEP_ds_b", "condition": {"and": [ADULT_RES, {"not": IS_CHIEF}, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kd_tauid")]}}, {"not": SETTLED}]}, "effect": [
                {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_m_other")},
                {"run_eocs": "PF_VIEW_read", "alpha_talker": g("pf_kd_ta")},
                {"if": m("pf_read_x > pf_kd_best"), "then": [
                    m("pf_kd_best = pf_read_x"), m("pf_kd_found = 1"),
                    {"copy_var": g("pf_kd_ta"), "target_var": g("pf_kd_a")}, {"copy_var": g("pf_kd_tauid"), "target_var": g("pf_kd_auid")}, {"copy_var": g("pf_kd_taname"), "target_var": g("pf_kd_aname")},
                    m("pf_kd_arole = pf_kd_tarole"), m("pf_kd_ahh = pf_kd_tahh"),
                    {"u_set_talker": g("pf_kd_b")}, {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kd_buid")}, name_into("pf_kd_bname"),
                    m("pf_kd_brole = value_or(u_pf_role, 0)"), m("pf_kd_bhh = value_or(u_pf_household, 0)")]}]}],
             "local": True, "npc_range": 60}]}], "local": True, "npc_range": 60},
    ], "u = avatar.  The worst quarrel in the place: of every grown-up who lives here (not the chief), whose own tension toward someone else here is highest (35+).  A pair settled at a meeting rests for 4 weeks (a ruling only takes the edge off; otherwise the same quarrel would top the list every week)."),
    eoc("PF_KEEP_dispute", topic + [
        m("pf_disputes_total = value_or(pf_disputes_total, 0) + 1"), m("pf_kd_last_t = time('now')"),
        {"copy_var": g("pf_kd_auid"), "target_var": g("pf_kd_last_a")}, {"copy_var": g("pf_kd_buid"), "target_var": g("pf_kd_last_b")},
        line("quarrel"),
        {"if": m("value_or(pf_kp_council, 0) == 1"), "then": [{"run_eocs": "PF_KEEP_council_judge"}], "else": [
        {"if": m("pf_kp_judge == 2"), "then": [
            {"set_string_var": "<global_val:pf_kd_aname> and <global_val:pf_kd_bname> want you to settle it: <global_val:pf_kd_topic>.  Do you side with <global_val:pf_kd_aname>?", "target_var": g("pf_kd_q1"), "parse_tags": True},
            {"set_string_var": "Do you side with <global_val:pf_kd_bname>, then?  (No: you tell them both to shake on it.)", "target_var": g("pf_kd_q2"), "parse_tags": True},
            {"if": {"u_query": g("pf_kd_q1"), "default": False}, "then": outcome("a", "b", "avatar") + [line("you_rule")],
             "else": [{"if": {"u_query": g("pf_kd_q2"), "default": False}, "then": outcome("b", "a", "avatar") + [line("you_rule")],
                       "else": SPLIT() + [line("you_split")]}]}],
         "else": [{"run_eocs": "PF_KEEP_judge", "alpha_talker": g("pf_kp_chief_t")}]}]},
    ], "u = avatar.  The quarrel is brought to the meeting.  If you're chief, you decide (side with one, or tell them to shake on it); otherwise the chief does.  Under a council, the council does (pass 6)."),
    eoc("PF_KEEP_judge", [
        name_into("pf_kd_judge"),
        {"copy_var": g("pf_kd_auid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"}, m("pf_kd_sa = pf_read_t + pf_read_w / 2 - pf_read_x"),
        {"copy_var": g("pf_kd_buid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"}, m("pf_kd_sb = pf_read_t + pf_read_w / 2 - pf_read_x"),
        {"if": m("abs(pf_kd_sa - pf_kd_sb) < 5"), "then": SPLIT() + [line("chief_split")],
         "else": [{"if": m("pf_kd_sa > pf_kd_sb"), "then": outcome("a", "b", "u") + [line("chief_rules")],
                   "else": outcome("b", "a", "u") + [line("chief_rules")]}]},
    ], "u = the chief.  They side with whoever they think more of (their own view: trust + warmth / 2 - tension); if it's close, both are told to shake on it.  The winner trusts the chief more, the loser resents them, and the two of them let some of it go either way."),
]

# ============================================================ THE CHIEF: death, the door, the menu
files["chief.json"] = [
    eoc("PF_KEEP_on_death", [
        name_into("pf_chief_dead_name"), m("pf_chiefs_lost_total = value_or(pf_chiefs_lost_total, 0) + 1"),
        {"if": m("value_or(pf_law_lord, 0) == 1"), "then": [{"run_eocs": "PF_KEEP_succession", "alpha_talker": "avatar"}],
         "else": [m("pf_chief_set = 0"), m("pf_mt_due = 1"), {"run_eocs": "PF_SAY_keep", "alpha_talker": "avatar", "variables": {"line": "chief_died"}}]},
    ], "The chief died: the chair is empty, and the place meets the next evening to choose again.  Under a lord, the heir takes the chair at once (or, with no heir, it's back to the meeting).",
        condition={"and": ["has_alpha", "u_is_npc", m("has_var(u_pf_uid)"), IS_CHIEF]},
        eoc_type="EVENT", required_event="character_dies"),
    eoc("PF_KEEP_door", [
        {"copy_var": g("pf_chief_uid"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
        {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_KEEP_door_decide", "alpha_talker": g("pf_find_who")}],
         "else": [{"if": {"u_query": g("pf_tj_q"), "default": True}, "then": [{"run_eocs": "PF_TOWN_join_yes"}], "else": [{"run_eocs": "PF_TOWN_join_no"}]}]},
    ], "u = avatar.  A family at the door when someone else is chief: it's the chief's call (if the chief isn't around, it's yours)."),
    eoc("PF_KEEP_door_decide", [
        name_into("pf_kd_judge"),
        m("_y = (value_or(pf_households_n, 0) < 4) + u_has_trait('PF_T_SOCIABLE') + u_has_trait('PF_Q_MOTHER_HEN')"),
        {"if": m("_y > 0"), "then": [line("door_yes"), {"run_eocs": "PF_TOWN_join_yes", "alpha_talker": "avatar"}],
         "else": [line("door_no"), {"run_eocs": "PF_TOWN_join_no", "alpha_talker": "avatar"}]},
        m("pf_chief_doors_total = value_or(pf_chief_doors_total, 0) + 1"),
    ], "u = the chief.  While the place is small (fewer than 4 households) they take people in; after that only a sociable or mother-hen chief keeps the door open."),
    eoc("PF_KEEP_menu", [
        m(f"pf_km_days = ({MEET_DAY} - {TODAY} % 7 + 7) % 7"),
        {"if": m("value_or(pf_mt_due, 0) == 1"), "then": [m("pf_km_days = 0")]},
        {"if": m("pf_km_days == 0"), "then": [{"set_string_var": "tonight", "target_var": g("pf_km_when")}],
         "else": [{"if": m("pf_km_days == 1"), "then": [{"set_string_var": "tomorrow evening", "target_var": g("pf_km_when")}],
                   "else": [{"set_string_var": "in <global_val:pf_km_days> days", "target_var": g("pf_km_when"), "parse_tags": True}]}]},
        m("pf_km_since = floor((time('now') - value_or(pf_chief_since, 0)) / time('1 d'))"),
        m("pf_km_days_c = pf_km_since"),
    ] + days_txt("pf_km_since", "pf_km_since_t") + [
        {"if": m("has_var(pf_heir_name) * (value_or(pf_heir_set, 0) == 1)"), "then": [{"copy_var": g("pf_heir_name"), "target_var": g("pf_km_heir")}],
         "else": [{"set_string_var": "nobody named yet", "target_var": g("pf_km_heir")}]},
        {"if": m("value_or(pf_law_lord, 0) == 1"), "then": [m("pf_km_lord = value_or(pf_chief_set, 0)")], "else": [m("pf_km_lord = 0")]},
        {"if": m("pf_km_lord == 1"), "then": [line("who_lord")]},
        {"if": m("pf_km_lord == 2"), "then": [line("who_you_lord")]},
        {"if": m(f"(pf_km_lord == 0) * ({COUNCIL_ON})"), "then": [
            {"run_eocs": "PF_KEEP_cn_list"}, m("pf_km_cn_days = max(28 - floor((time('now') - value_or(pf_cn_since, 0)) / time('1 d')), 0)"), line("who_council")]},
        {"if": m(f"(pf_km_lord == 0) * (({COUNCIL_ON}) == 0)"), "then": [{"switch": m("value_or(pf_chief_set, 0)"), "cases": [
            {"case": 0, "effect": [{"run_eocs": "PF_KEEP_count"},
                                   {"if": m(f"pf_kp_n >= {MIN_ADULTS}"), "then": [line("who_none")], "else": [line("who_small")]}]},
            {"case": 1, "effect": [line("who_npc")]},
            {"case": 2, "effect": [line("who_you")]}]}]},
    ], "u = avatar.  Home menu: Who's in charge.", condition=m(AT_HOME)),
    eoc("PF_KEEP_call_now", [m("pf_mt_due = 1"), {"if": m(f"{HOUR} < 21"), "then": [line("you_call_tonight")], "else": [line("you_call")]}],
        "u = avatar.  Home menu: Call a meeting (if you're chief): tomorrow evening, or tonight if it's not yet late.",
        condition={"and": [m(AT_HOME), m("value_or(pf_chief_set, 0) == 2"), m("value_or(pf_mt_due, 0) == 0")]}),
]

# ============================================================ LINES
P = "<global_val:pf_kp_place>"
A, B, J, W, L, CN = ("<global_val:pf_kd_aname>", "<global_val:pf_kd_bname>", "<global_val:pf_kd_judge>",
                     "<global_val:pf_kd_wname>", "<global_val:pf_kd_lname>", "<global_val:pf_chief_name>")
VOTES = "<global_val:pf_kw_best> of <global_val:pf_ke_total>"
LINES = {
    "call_first": ("Somebody bangs a pot and calls everyone over.  \"If we're going to live like this, we'd better start deciding things together.\"", "info"),
    "call_0": ("Somebody bangs a pot: meeting tonight.  People drift over, grumbling, with their chairs.", "info"),
    "call_1": ("Word goes round that there's a meeting tonight.  People finish what they're doing and come over.", "info"),
    "call_2": ("Meeting night.  Somebody has already set out the chairs in a rough circle.", "info"),
    "first": (f"The first meeting {P} has ever held.  Nobody knows how to run one, so everyone talks at once.", "info"),
    "open_0": ("The meeting sits.  Somebody reads out a list that nobody asked for.", "info"),
    "open_1": ("The meeting sits.  It starts with the leaking roof, as it always does.", "info"),
    "open_2": ("The meeting sits.  The children are sent off to play, and mostly don't go.", "info"),
    "quiet_0": ("It's a quiet one: the latrine, again.  It takes an hour.", "info"),
    "quiet_1": ("Nothing much to settle.  It turns into stories, and then into somebody's bottle.", "good"),
    "quiet_2": ("A quiet meeting: who's going out scavenging, and where not to go.  Everyone's home by dark.", "info"),
    "quiet_3": ("They spend the whole meeting arguing about a name for the dog.  Nobody wins.", "good"),
    "chief_absent": (f"{CN} isn't here tonight.  The meeting goes on without its chief, and decides nothing.", "info"),
    "chief_gone": (f"{CN} hasn't been seen at two meetings running.  The chair is empty, and someone says it out loud.", "bad"),
    "chief_died": (f"<global_val:pf_chief_dead_name> is dead, and the place has no chief.  People look at each other.  Then at you.", "bad"),
    "confidence": (f"Somebody finally says it: {CN} isn't working out.  More hands go up than anyone expected.  It goes to a vote.", "bad"),
    "no_chief": ("Hardly anyone will put their hand up for anybody.  The place goes on without a chief for now.", "info"),
    "elected_0": (f"<global_val:pf_kw_name> is chief, {VOTES} votes.  They look like they'd rather not be.", "good"),
    "elected_1": (f"The hands go up for <global_val:pf_kw_name>: {VOTES}.  Somebody claps them on the back.  \"Your problem now.\"", "good"),
    "kept": (f"<global_val:pf_kw_name> keeps the chair, {VOTES}.  They let out a breath they'd been holding all night.", "good"),
    "elected_you": (f"They choose you, {VOTES}.  Somebody starts clapping, and then everyone does.", "good"),
    "kept_you": (f"They keep you on, {VOTES}.  Not everyone looks happy about it.", "good"),
    "quarrel": (f"{A} and {B} bring a quarrel to the meeting: <global_val:pf_kd_topic>.", "info"),
    "chief_rules": (f"{J} hears them both out, and rules for {W}.  {L} doesn't say anything for the rest of the night.", "info"),
    "chief_split": (f"{J} hears them both out and tells them they're both wrong, and to shake on it.  Eventually, they do.", "good"),
    "you_rule": (f"You rule for {W}.  {L} takes it badly, but the matter's closed.", "info"),
    "you_split": (f"You tell {A} and {B} to shake on it.  They do, eventually, and the meeting lets out a breath.", "good"),
    "door_yes": (f"{J} is chief, so it's their call.  \"More hands.  Find them a roof.\"", "good"),
    "door_no": (f"{J} is chief, so it's their call.  \"Not this time.  We can't keep who we've got.\"", "bad"),
    "deposed": ("<global_val:pf_kp_old_name> hands over the keys to the stores without a word, and keeps to themselves for the rest of the day.", "bad"),
    "deposed_kept": ("<global_val:pf_kp_old_name> keeps the chair, by a thread, and knows exactly whose hands stayed down.", "info"),
    "deposed_you": ("You hand over the keys.  Nobody quite meets your eye, and then somebody does, and nods.", "bad"),
    "deposed_kept_you": ("You keep the chair, by a thread.  You know exactly whose hands went up.", "info"),
    "who_none": ("Nobody's in charge yet.  The next meeting (<global_val:pf_km_when>) will choose.", "info"),
    # full run: "(4 grown-ups living here, …)" read as the current count; say both numbers plainly
    "meet_too_few": ("It's meeting night, and there's nobody to meet: <global_val:pf_kp_n> grown-ups live here besides you.  Nobody stacks the chairs out.  Someone says what everyone's thinking: this isn't a town anymore, just a family hanging on.  Meetings start again with 4 grown-ups.", "bad"),
    "who_small": ("Nobody's in charge.  <global_val:pf_kp_n> grown-ups live here besides you; once there are 4, the place will start holding meetings.", "info"),
    "who_npc": (f"{CN} is chief, for <global_val:pf_km_since_t> now.  Next meeting: <global_val:pf_km_when>.", "info"),
    "who_you": ("You're chief, for <global_val:pf_km_since_t> now.  Next meeting: <global_val:pf_km_when>.", "info"),
    "you_call": ("You put the word out: meeting tomorrow evening.", "info"),
    "you_call_tonight": ("You put the word out: meeting this evening.", "info"),
}
files["lines.json"] = [eoc("PF_SAY_keep", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Keep lines, picked by the context var 'line'.")]

# ============================================================ LAB (listed in the Home lab by gen_home.py)
def nearest(var, exclude=None):
    cond = [ADULT_RES, {"not": IS_CHIEF}]
    if exclude:
        cond.append({"not": {"compare_string": [{"u_val": "pf_uid"}, g(exclude)]}})
    return [m("pf_hl_d = 99"), {"u_location_variable": g("pf_hl_av")},
            {"u_run_npc_eocs": [{"id": f"PF_KL_near_{var}", "condition": {"and": cond}, "effect": [
                {"u_location_variable": {"u_val": "pf_pos"}},
                {"if": m("distance(u_pf_pos, pf_hl_av) < pf_hl_d"), "then": [m("pf_hl_d = distance(u_pf_pos, pf_hl_av)"), {"u_set_talker": g(var)},
                                                                             {"copy_var": {"u_val": "pf_uid"}, "target_var": g(var + "_uid")}, name_into(var + "_name")]}]}],
             "local": True, "npc_range": 30}]
files["lab_keep.json"] = [
    eoc("PF_KL_meet", [{"run_eocs": "PF_KEEP_count"},
                       {"if": m("pf_kp_n >= 2"), "then": [{"run_eocs": "PF_KEEP_agenda"}], "else": [say("[keep lab] Fewer than 2 grown-ups who live here are in range.")]}],
        "Keep lab: the meeting sits now (skips the call and the 4-adult rule)."),
    eoc("PF_KL_fallout", nearest("pf_kl_a") + [
        {"if": m("pf_hl_d < 99"), "then": nearest("pf_kl_b", "pf_kl_a_uid") + [
            {"if": m("pf_hl_d < 99"), "then": [
                m("pf_m_str_in = 100"), {"run_eocs": "PF_MK_argument", "alpha_talker": g("pf_kl_a"), "beta_talker": g("pf_kl_b")},
                m("pf_m_str_in = 100"), {"run_eocs": "PF_MK_argument", "alpha_talker": g("pf_kl_b"), "beta_talker": g("pf_kl_a")},
                say("[keep lab] <global_val:pf_kl_a_name> and <global_val:pf_kl_b_name> (the two grown-ups nearest you, not the chief) have had a row, twice.")],
             "else": [say("[keep lab] Only one grown-up who lives here is near.")]}],
         "else": [say("[keep lab] Nobody who lives here is near.")]}]),
    eoc("PF_KL_dissent", [
        {"if": m("value_or(pf_chief_set, 0) == 0"), "then": [say("[keep lab] There's no chief.")], "else": [
            {"if": m("pf_chief_set == 2"), "then": [{"set_string_var": "AVATAR", "target_var": g("pf_kl_target")}], "else": [{"copy_var": g("pf_chief_uid"), "target_var": g("pf_kl_target")}]},
            {"u_run_npc_eocs": [{"id": "PF_KL_turn", "condition": {"and": [ADULT_RES, {"not": IS_CHIEF}]}, "effect": [
                {"copy_var": g("pf_kl_target"), "target_var": g("pf_m_other")}, m("pf_mv_role = 1"), m("pf_m_str_in = 90"), {"run_eocs": "PF_MV_betrayal"}]}],
             "local": True, "npc_range": 60},
            say("[keep lab] Everyone who lives here now feels betrayed by the chief.")]}]),
    eoc("PF_KL_vacant", [m("pf_chief_set = 0"), m("pf_mt_due = 1"), say("[keep lab] The chair is empty; the next evening holds a meeting.")]),
    eoc("PF_KL_stats", [
        m("pf_hs_a = value_or(pf_meetings_total, 0)"), m("pf_hs_b = value_or(pf_elections_total, 0)"), m("pf_hs_c = value_or(pf_disputes_total, 0)"),
        m("pf_hs_d = value_or(pf_confidence_total, 0)"), m("pf_hs_e = value_or(pf_chief_set, 0)"),
        say("[keep lab] meetings <global_val:pf_hs_a>, elections <global_val:pf_hs_b>, quarrels <global_val:pf_hs_c>, confidence votes <global_val:pf_hs_d>, chief <global_val:pf_hs_e> (0 none, 1 someone, 2 you): <global_val:pf_chief_name>.")]),
]


# ============================================================ PASS 2: LAWS AND THE TITHE
# Each law: id, key, short name, what it says (for 'that ...'), the voter's own support (u = voter: temperament, job, what has
# happened lately), when someone brings it up unasked (globals), and who tends to propose it (u = a candidate proposer).
LAWS = [
    (1, "watch", "everyone takes a turn on the watch", "everyone takes a turn on the watch, not just the guards",
     "(value_or(u_pf_role, 0) == 2) * 3 - (value_or(u_pf_role, 0) == 1) + u_has_trait('PF_Q_LOYAL') - u_has_trait('PF_T_LONER') + rand(2) - 1",
     "value_or(pf_wt_nights_total, 0) >= 3", "value_or(u_pf_role, 0) == 2"),
    (2, "dark", "no strangers after dark", "nobody new comes in after dark: they wait outside till morning",
     "u_has_trait('PF_Q_GRUDGE') * 2 + u_has_trait('PF_T_LONER') * 2 - u_has_trait('PF_T_SOCIABLE') * 2 - u_has_trait('PF_Q_MOTHER_HEN') * 2 + (time('now') - value_or(pf_horn_t, -999999) < time('7 d')) * 2 + rand(2) - 1",
     "(time('now') - value_or(pf_horn_t, -999999) < time('7 d')) * (value_or(pf_households_n, 0) >= 1)", "u_has_trait('PF_Q_GRUDGE') + u_has_trait('PF_T_LONER') > 0"),
    (3, "tithe", "a tithe to the stores", "every household puts a share of its work into the common stores",
     "u_has_trait('PF_Q_HATES_WASTE') * 3 + (value_or(u_pf_role, 0) == 1) * 2 - u_has_trait('PF_T_LONER') * 2 - u_has_trait('PF_Q_PROUD') + (value_or(pf_stores, 0) < 10) + rand(2) - 1",
     "(value_or(pf_stores, 0) < 10) * (value_or(pf_households_n, 0) >= 1)", "u_has_trait('PF_Q_HATES_WASTE') + (value_or(u_pf_role, 0) == 1) > 0"),
    (4, "rest", "a rest day", "meeting day is a day of rest: no chores, no work, just each other",
     "u_has_trait('PF_T_SOCIABLE') * 3 + u_has_trait('PF_Q_GALLOWS') - u_has_trait('PF_Q_HATES_WASTE') * 2 - (value_or(u_pf_role, 0) == 7) + rand(2) - 1",
     "value_or(pf_disputes_total, 0) >= 2", "u_has_trait('PF_T_SOCIABLE') > 0"),
    (5, "door", "the meeting decides who moves in", "the whole meeting decides who moves in, not one person",
     "u_has_trait('PF_Q_GRUDGE') + u_has_trait('PF_T_LONER') + u_has_trait('PF_Q_PROUD') + (value_or(pf_households_n, 0) >= 3) * 2 - u_has_trait('PF_T_SOCIABLE') + rand(2) - 1",
     "value_or(pf_households_n, 0) >= 2", "u_has_trait('PF_Q_GRUDGE') + u_has_trait('PF_T_LONER') + u_has_trait('PF_Q_PROUD') > 0"),
    (6, "lord", "a lord for life", "the chief rules for life, and their heir after them",
     "u_has_trait('PF_Q_LOYAL') * 2 + u_has_trait('PF_Q_MOTHER_HEN') - u_has_trait('PF_Q_PROUD') * 2 - u_has_trait('PF_T_LONER') * 2 + rand(2) - 1",
     "(value_or(pf_law_council, 0) == 0) * (value_or(pf_chief_set, 0) > 0) * (time('now') - value_or(pf_chief_since, 0) >= time('14 d')) * (value_or(pf_elections_total, 0) >= 2)", "u_has_trait('PF_Q_LOYAL') > 0"),
    # pass 6: the council (the proud want a voice, the loyal want one leader; the voter's distrust of the chief is added in the vote)
    (7, "council", "a council of three", "the place is run by a council of three, chosen by the meeting, not by one chief",
     "u_has_trait('PF_Q_PROUD') * 2 + u_has_trait('PF_Q_GRUDGE') + u_has_trait('PF_T_SOCIABLE') - u_has_trait('PF_Q_LOYAL') * 2 - u_has_trait('PF_T_LONER') + (value_or(pf_disputes_total, 0) >= 3) + rand(2) - 1",
     "(value_or(pf_law_lord, 0) == 0) * ((value_or(pf_confidence_total, 0) + value_or(pf_coups_total, 0) >= 1) + (value_or(pf_disputes_total, 0) >= 3) * (value_or(pf_households_n, 0) >= 2) > 0)",
     "u_has_trait('PF_Q_PROUD') + u_has_trait('PF_Q_GRUDGE') > 0"),
]
EXCLUSIVE = {"lord": "council", "council": "lord"}   # a lord and a council can't both be law
NL = len(LAWS)
REST_DAY = f"(value_or(pf_law_rest, 0) == 1) * ({TODAY} % 7 == {MEET_DAY})"
law_name = [{"if": m(f"pf_kl_law == {i}"), "then": [{"set_string_var": nm, "target_var": g("pf_kl_name")}, {"set_string_var": txt, "target_var": g("pf_kl_text")}]}
            for i, k, nm, txt, sup, trig, pref in LAWS]
law_support = [{"if": m(f"pf_kl_law == {i}"), "then": [m(f"_b = {sup}")]} for i, k, nm, txt, sup, trig, pref in LAWS]
law_inforce = [{"if": m(f"pf_kl_law == {i}"), "then": [m(f"pf_kl_in = value_or(pf_law_{k}, 0)")]} for i, k, nm, txt, sup, trig, pref in LAWS]
law_trigger = [{"if": m(f"pf_kl_law == {i}"), "then": [m(f"pf_kl_trig = {trig}")]} for i, k, nm, txt, sup, trig, pref in LAWS]
law_pref = [{"if": m(f"pf_kl_law == {i}"), "then": [m(f"_pf = {pref}")]} for i, k, nm, txt, sup, trig, pref in LAWS]
law_set = [{"if": m(f"pf_kl_law == {i}"), "then": [m(f"pf_law_{k} = pf_kl_rep == 1 ? 0 : 1"), m(f"pf_law_{k}_t = time('now')")]} for i, k, nm, txt, sup, trig, pref in LAWS]
# an unasked proposal: start at a random law and take the first that someone has a reason to bring up
try_law = []
for step in range(NL):
    try_law.append({"if": m("pf_kl_law == 0"), "then": [
        m(f"pf_kl_try = (pf_kl_start + {step}) % {NL} + 1"), m("pf_kl_law = pf_kl_try")] + law_inforce + law_trigger + [
        {"if": m("(pf_kl_in == 0) * ((pf_kl_trig > 0) + value_or(pf_kl_force, 0) > 0)"), "then": [m("pf_kl_rep = 0")],
         "else": [{"if": m("(pf_kl_in == 1) * (rand(2) == 0)"), "then": [m("pf_kl_rep = 1")], "else": [m("pf_kl_law = 0")]}]}]})
files["laws.json"] = [
    {"type": "morale_type", "id": "PF_morale_rest", "text": "The rest day"},
    eoc("PF_KEEP_law_step", [
        m("pf_kl_law = 0"), m("pf_kl_rep = 0"), m("pf_kl_byyou = 0"),
        {"if": m("value_or(pf_kp_prop, 0) > 0"), "then": [m("pf_kl_law = pf_kp_prop"), m("pf_kl_rep = value_or(pf_kp_prop_rep, 0)"), m("pf_kl_byyou = 1"), m("pf_kp_prop = 0")],
         "else": [{"if": {"or": [m("value_or(pf_kl_force, 0) == 1"), m("rand(1) == 0")]}, "then": [m(f"pf_kl_start = rand({NL - 1})")] + try_law}]},
        {"if": m("pf_kl_law > 0"), "then": [{"run_eocs": "PF_KEEP_law_vote"}]},
    ], "u = avatar.  One law per meeting: the one you put to it, or (one meeting in two) one somebody has a reason to bring up: a law not yet in force whose moment has come (a third shift for the same guards, a fight this week, stores running low, quarrels piling up, more households), or a law in force that someone wants gone (one time in three)."),
    eoc("PF_KEEP_law_vote", law_name + [
        m("pf_kp_events += 1"), m("pf_kl_yes = 0"), m("pf_kl_no = 0"), m("pf_kl_lordseen = 0"), m("pf_kl_youv = -1"),
        {"if": m("pf_kl_byyou == 1"),
         "then": [{"set_string_var": "AVATAR", "target_var": g("pf_kl_puid")}, {"set_string_var": "you", "target_var": g("pf_kl_pname")}, m("pf_kl_yes = 1"), m("pf_kl_youv = 1")],
         "else": [m("pf_kl_got = 0"),
                  {"u_run_npc_eocs": [{"id": "PF_KEEP_proposer_pref", "condition": {"and": [ADULT_RES, m("pf_kl_got == 0")]}, "effect": law_pref + [
                      {"if": m("_pf > 0"), "then": [m("pf_kl_got = 1"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kl_puid")}, name_into("pf_kl_pname")]}]}],
                   "local": True, "npc_range": 60},
                  {"u_run_npc_eocs": [{"id": "PF_KEEP_proposer_any", "condition": {"and": [ADULT_RES, m("pf_kl_got == 0")]}, "effect": [
                      m("pf_kl_got = 1"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kl_puid")}, name_into("pf_kl_pname")]}],
                   "local": True, "npc_range": 60},
                  m("pf_kl_yes = 1")]},
        {"if": m("pf_kl_byyou == 1"),
         "then": [{"if": m("pf_kl_rep == 1"), "then": [line("law_put_repeal_you")], "else": [line("law_put_you")]}],
         "else": [{"if": m("pf_kl_rep == 1"), "then": [line("law_put_repeal")], "else": [line("law_put")]}]},
        {"u_run_npc_eocs": ["PF_KEEP_law_voter"], "local": True, "npc_range": 60},
        {"if": m("(pf_kl_byyou == 0) * (distance(pf_kp_av, pf_home_loc) <= 30)"), "then": [
            {"if": m("pf_kl_rep == 1"),
             "then": [{"set_string_var": "<global_val:pf_kl_pname> wants to do away with the law that <global_val:pf_kl_text>.  Do you vote to do away with it?", "target_var": g("pf_kl_q"), "parse_tags": True}],
             "else": [{"set_string_var": "<global_val:pf_kl_pname> proposes a law: that <global_val:pf_kl_text>.  Do you vote for it?", "target_var": g("pf_kl_q"), "parse_tags": True}]},
            {"if": {"u_query": g("pf_kl_q"), "default": False}, "then": [m("pf_kl_yes += 1"), m("pf_kl_youv = 1")], "else": [m("pf_kl_no += 1"), m("pf_kl_youv = 0")]}]},
        m("pf_kl_pass = pf_kl_yes > pf_kl_no"), m("pf_kl_over = 0"),
        # under a lord, the lord's word is final (yours, if you're the lord)
        {"if": m("value_or(pf_law_lord, 0) == 1"), "then": [
            {"if": m("(value_or(pf_chief_set, 0) == 2) * (pf_kl_youv >= 0) * (pf_kl_youv != pf_kl_pass)"), "then": [m("pf_kl_pass = pf_kl_youv"), m("pf_kl_over = 1"), line("law_you_overrule")]},
            {"if": m("(value_or(pf_chief_set, 0) == 1) * value_or(pf_kl_lordseen, 0) * (pf_kl_lordv != pf_kl_pass)"), "then": [m("pf_kl_pass = pf_kl_lordv"), m("pf_kl_over = 1"), line("law_lord_overrule")]}]},
        # a lord needs someone to crown
        {"if": m("(pf_kl_law == 6) * (pf_kl_rep == 0) * (value_or(pf_chief_set, 0) == 0)"), "then": [m("pf_kl_pass = 0")]},
        # a lord and a council can't both be law
        {"if": m("(pf_kl_law == 6) * (pf_kl_rep == 0) * (value_or(pf_law_council, 0) == 1)"), "then": [m("pf_kl_pass = 0")]},
        {"if": m("(pf_kl_law == 7) * (pf_kl_rep == 0) * (value_or(pf_law_lord, 0) == 1)"), "then": [m("pf_kl_pass = 0")]},
        {"if": m("pf_kl_pass == 1"),
         "then": law_set + [{"if": m("pf_kl_over == 1"), "then": [{"if": m("pf_kl_rep == 1"), "then": [line("law_repealed_lord")], "else": [line("law_passed_lord")]}],
                             "else": [{"if": m("pf_kl_rep == 1"), "then": [line("law_repealed")], "else": [line("law_passed")]}]},
                            m("pf_laws_passed_total = value_or(pf_laws_passed_total, 0) + 1"),
                            # the council: chosen at the next meeting; done away with, the speaker keeps the chair
                            {"if": m("pf_kl_law == 7"), "then": [m("pf_cn_n = 0"), m("pf_cn_term = value_or(pf_cn_term, 0) + 1"),
                                                                 {"if": m("pf_kl_rep == 1"), "then": [line("council_gone")], "else": [line("council_law")]}]}],
         "else": [{"if": m("pf_kl_over == 1"), "then": [{"if": m("pf_kl_rep == 1"), "then": [line("law_kept_lord")], "else": [line("law_failed_lord")]}],
                   "else": [{"if": m("pf_kl_rep == 1"), "then": [line("law_kept")], "else": [line("law_failed")]}]},
                  m("pf_laws_failed_total = value_or(pf_laws_failed_total, 0) + 1")]},
    ], "u = avatar.  Who proposes it (you; or someone it suits, else anyone), then everyone who lives here votes from their own temperament, job and what has happened lately, plus a tenth of their trust in whoever proposed it; you vote too (a popup) if you're there.  The proposer votes for it.  More for than against: it passes."),
    eoc("PF_KEEP_law_voter", law_support + [
        {"if": m("(pf_kl_law == 6) * (value_or(pf_chief_set, 0) > 0)"), "then": [
            {"if": m("pf_chief_set == 2"), "then": [{"set_string_var": "AVATAR", "target_var": g("pf_m_other")}], "else": [{"copy_var": g("pf_chief_uid"), "target_var": g("pf_m_other")}]},
            {"run_eocs": "PF_VIEW_read"}, m("_b += (pf_read_t - 20) / 5")]},
        # the chief always backs their own lordship (they have no view of themselves to weigh)
        {"if": {"and": [m("pf_kl_law == 6"), m("value_or(pf_chief_set, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_chief_uid")]}]}, "then": [m("_b = 10")]},
        # a council: the less they trust the chief, the more they want one; the chief would rather keep the chair (unless sociable)
        {"if": m("(pf_kl_law == 7) * (value_or(pf_chief_set, 0) > 0)"), "then": [
            {"if": m("pf_chief_set == 2"), "then": [{"set_string_var": "AVATAR", "target_var": g("pf_m_other")}], "else": [{"copy_var": g("pf_chief_uid"), "target_var": g("pf_m_other")}]},
            {"run_eocs": "PF_VIEW_read"}, m("_b += (15 - pf_read_t) / 5")]},
        {"if": {"and": [m("pf_kl_law == 7"), m("value_or(pf_chief_set, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_chief_uid")]}]},
         "then": [m("_b = u_has_trait('PF_T_SOCIABLE') * 3 - 2")]},
        {"if": m("pf_kl_rep == 1"), "then": [m("_b = -_b")]},
        {"copy_var": g("pf_kl_puid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        m("_b += pf_read_t / 10"),
        {"if": m("_b > 0"), "then": [m("pf_kl_yes += 1")], "else": [m("pf_kl_no += 1")]},
        {"if": {"and": [m("value_or(pf_chief_set, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_chief_uid")]}]},
         "then": [m("pf_kl_lordseen = 1"), m("pf_kl_lordv = _b > 0")]},
    ], "u = a grown-up who lives here (not the proposer): their vote.",
        condition={"and": [ADULT_RES, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kl_puid")]}}]}),
    # ---------------- putting a law to the meeting yourself (Home menu), and the list of laws
    eoc("PF_KEEP_propose_menu", [
        {"run_eoc_selector": [f"PF_KEEP_prop_{k}" for i, k, nm, txt, sup, trig, pref in LAWS] + [f"PF_KEEP_rep_{k}" for i, k, nm, txt, sup, trig, pref in LAWS],
         "names": [f"Propose: {nm}" for i, k, nm, txt, sup, trig, pref in LAWS] + [f"Do away with: {nm}" for i, k, nm, txt, sup, trig, pref in LAWS],
         "descriptions": [f"Put it to the next meeting: that {txt}." for i, k, nm, txt, sup, trig, pref in LAWS] +
                         [f"Ask the next meeting to do away with the law that {txt}." for i, k, nm, txt, sup, trig, pref in LAWS],
         "keys": [str(i) for i in range(1, NL + 1)] + list("abcdefghijk"[:NL]), "title": "Put a law to the meeting", "hide_failing": True, "allow_cancel": True},
    ], "u = avatar.  Home menu: Put a law to the meeting.", condition={"and": [m(AT_HOME), m("value_or(pf_kp_prop, 0) == 0")]}),
] + [eoc(f"PF_KEEP_prop_{k}", [m(f"pf_kp_prop = {i}"), m("pf_kp_prop_rep = 0"), m(f"pf_kl_law = {i}")] + law_name + [line("you_propose")],
         condition=m(f"(value_or(pf_law_{k}, 0) == 0) * (value_or(pf_law_{EXCLUSIVE[k]}, 0) == 0)" if k in EXCLUSIVE else f"value_or(pf_law_{k}, 0) == 0"))
    for i, k, nm, txt, sup, trig, pref in LAWS] + [
    eoc(f"PF_KEEP_rep_{k}", [m(f"pf_kp_prop = {i}"), m("pf_kp_prop_rep = 1"), m(f"pf_kl_law = {i}")] + law_name + [line("you_propose_repeal")],
        condition=m(f"value_or(pf_law_{k}, 0) == 1")) for i, k, nm, txt, sup, trig, pref in LAWS] + [
    eoc("PF_KEEP_laws_menu", [m("pf_kl_n = 0")] + [
        {"if": m(f"value_or(pf_law_{k}, 0) == 1"), "then": [m("pf_kl_n += 1"), m(f"pf_kl_law = {i}"),
                                                           m(f"pf_kl_days = floor((time('now') - pf_law_{k}_t) / time('1 d'))")] + days_txt("pf_kl_days", "pf_kl_days_t") + law_name + [line("law_list")]}
        for i, k, nm, txt, sup, trig, pref in LAWS] + [
        {"if": m("pf_kl_n == 0"), "then": [line("law_none")]},
        {"if": m("value_or(pf_kp_prop, 0) > 0"), "then": [m("pf_kl_law = pf_kp_prop")] + law_name + [line("law_pending")]},
    ], "u = avatar.  Home menu: The laws of the place.", condition=m(AT_HOME)),
    # ---------------- the tithe
    eoc("PF_KEEP_tithe_one", [
        {"if": {"and": [m("value_or(pf_tithe_shirk, 0) == 0"), m("u_has_trait('PF_T_LONER') + u_has_trait('PF_Q_PROUD') > 0"), m("rand(11) == 0")]},
         "then": [m("pf_tithe_shirk = 1"), m("u_pf_shirks = value_or(u_pf_shirks, 0) + 1"),
                  {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_tithe_shirk_uid")}, name_into("pf_tithe_shirk_name")],
         "else": [m("pf_stores = value_or(pf_stores, 0) + 1"), m("pf_tithe_week = value_or(pf_tithe_week, 0) + 1"), m("pf_tithe_total = value_or(pf_tithe_total, 0) + 1")]},
    ], "u = someone who lives here and just did their chore (household.json), with the tithe in force: a share goes to the stores (+1).  Now and then a loner or a proud one keeps theirs back (the first each week is noticed)."),
    eoc("PF_KEEP_tithe_step", [
        {"if": m("value_or(pf_law_tithe, 0) == 1"), "then": [
            {"if": m("value_or(pf_tithe_week, 0) > 0"), "then": [m("pf_kp_events += 1"), line("tithe_report")]},
            m("pf_tithe_week = 0"),
            {"if": m("value_or(pf_tithe_shirk, 0) == 1"), "then": [
                m("pf_tithe_shirk = 0"), m("pf_kp_events += 1"), line("tithe_shirk"),
                {"if": m("pf_kp_judge == 2"), "then": [
                    {"set_string_var": "<global_val:pf_tithe_shirk_name> kept back their share of the tithe.  Do you fine them?", "target_var": g("pf_kt_q"), "parse_tags": True},
                    {"if": {"u_query": g("pf_kt_q"), "default": False},
                     "then": [m("pf_stores = value_or(pf_stores, 0) + 3"), {"run_eocs": "PF_KEEP_tithe_fine", "alpha_talker": "avatar"}, line("tithe_fined_you")],
                     "else": [line("tithe_let_go")]}],
                 "else": [{"if": m("pf_kp_judge == 1"), "then": [m("pf_stores = value_or(pf_stores, 0) + 3"), {"run_eocs": "PF_KEEP_tithe_fine", "alpha_talker": g("pf_kp_chief_t")}, line("tithe_fined")],
                           "else": [line("tithe_nobody")]}]}]}]},
    ], "u = avatar.  With the tithe in force: what it brought in this week, and anyone who kept their share back.  The chief fines them (3 into the stores) and they resent it; if you're chief, you decide; with no chief, nobody holds them to it."),
    eoc("PF_KEEP_tithe_fine", [
        name_into("pf_kd_judge"),
        {"copy_var": g("pf_tithe_shirk_uid"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
        {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_MK_ruled_against", "beta_talker": g("pf_find_who")}]},
    ], "u = the chief (or you): the one who kept their share back resents the fine (ruled_against), if they're here."),
    # ---------------- the rest day
    eoc("PF_KEEP_rest_tick", [
        m(f"pf_rest_day = {TODAY}"),
        {"u_location_variable": g("pf_kp_av")},
        {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [{"run_eocs": "PF_KEEP_rest_now"}]},
    ], "Once on the rest day, 07:00-10:00, with the rest-day law in force and you at home: nobody works (chores and the workday skip the day), and the day is spent together.",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m(REST_DAY), m(f"{HOUR} >= 7"), m(f"{HOUR} < 10"), m(f"value_or(pf_rest_day, -1) != {TODAY}")]}),
    eoc("PF_KEEP_rest_now", [
        {"u_add_morale": "PF_morale_rest", "bonus": 8, "max_bonus": 8, "duration": "14 hours", "decay_start": "8 hours"},
        {"u_run_npc_eocs": [{"id": "PF_KEEP_rest_one", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), m("has_var(u_pf_uid)")]},
                             "effect": [m("pf_m_str_in = 20"), {"run_eocs": "PF_MK_fire_evening", "beta_talker": "avatar"}]}], "local": True, "npc_range": 60},
        {"if": m(CALM), "then": pool("rest", 3)},
        m("pf_rest_days_total = value_or(pf_rest_days_total, 0) + 1"),
    ], "u = avatar.  The rest day: 'The rest day' morale (+8), and a quiet time together with everyone who lives here."),
    # ---------------- the door, by the whole meeting
    eoc("PF_KEEP_door_vote", [
        m("pf_kv_dyes = 0"), m("pf_kv_dno = 0"),
        {"u_run_npc_eocs": [{"id": "PF_KEEP_door_voter", "condition": ADULT_RES, "effect": [
            m("_b = 1 + u_has_trait('PF_T_SOCIABLE') * 2 + u_has_trait('PF_Q_MOTHER_HEN') * 2 - u_has_trait('PF_T_LONER') * 2 - u_has_trait('PF_Q_GRUDGE') - (value_or(pf_households_n, 0) >= 4) * 2 + rand(2) - 1"),
            {"if": m("_b > 0"), "then": [m("pf_kv_dyes += 1")], "else": [m("pf_kv_dno += 1")]}]}], "local": True, "npc_range": 60},
        {"set_string_var": "<global_val:pf_tj_name> and their family are at the door with everything they own, asking to live here.  By the law of the place, the meeting decides.  Do you vote to take them in?", "target_var": g("pf_kv_dq"), "parse_tags": True},
        {"if": {"u_query": g("pf_kv_dq"), "default": True}, "then": [m("pf_kv_dyes += 1")], "else": [m("pf_kv_dno += 1")]},
        {"if": m("pf_kv_dyes > pf_kv_dno"), "then": [line("door_vote_yes"), {"run_eocs": "PF_TOWN_join_yes"}],
         "else": [line("door_vote_no"), {"run_eocs": "PF_TOWN_join_no"}]},
    ], "u = avatar.  With the door law in force, the family at the door is put to everyone who lives here (sociable and mother-hen people say yes, loners and grudge-holders no, fewer once there are 4+ households) and to you."),
]
LINES.update({
    "law_put": ("<global_val:pf_kl_pname> stands up: they want a law that <global_val:pf_kl_text>.", "info"),
    "law_put_repeal": ("<global_val:pf_kl_pname> stands up: they want to do away with the law that <global_val:pf_kl_text>.", "info"),
    "law_put_you": ("You stand up and put it to them: a law that <global_val:pf_kl_text>.", "info"),
    "law_put_repeal_you": ("You stand up and put it to them: do away with the law that <global_val:pf_kl_text>.", "info"),
    "law_passed": ("It passes, <global_val:pf_kl_yes> to <global_val:pf_kl_no>.  From now on, <global_val:pf_kl_text>.", "good"),
    "law_failed": ("It's voted down, <global_val:pf_kl_yes> to <global_val:pf_kl_no>.", "info"),
    "law_repealed": ("It goes, <global_val:pf_kl_yes> to <global_val:pf_kl_no>.  No more '<global_val:pf_kl_name>'.", "info"),
    "law_kept": ("The law stays, <global_val:pf_kl_no> to <global_val:pf_kl_yes>.", "info"),
    "you_propose": ("You'll put it to the next meeting: that <global_val:pf_kl_text>.", "info"),
    "you_propose_repeal": ("You'll ask the next meeting to do away with '<global_val:pf_kl_name>'.", "info"),
    "law_list": ("The law: <global_val:pf_kl_text>.  (In force for <global_val:pf_kl_days_t>.)", "info"),
    "law_none": ("The place has no laws yet, beyond the ones everybody just knows.", "info"),
    "law_pending": ("Up at the next meeting: '<global_val:pf_kl_name>'.", "info"),
    "tithe_report": ("The tithe brought <global_val:pf_tithe_week> into the stores this week.", "info"),
    "tithe_shirk": ("Somebody brings it up: <global_val:pf_tithe_shirk_name> has been keeping back their share of the tithe.", "bad"),
    "tithe_fined": ("<global_val:pf_kd_judge> makes <global_val:pf_tithe_shirk_name> pay it back, with some on top.  They pay.  They don't like it.", "info"),
    "tithe_fined_you": ("You make <global_val:pf_tithe_shirk_name> pay it back, with some on top.  They pay.  They don't look at you.", "info"),
    "tithe_let_go": ("You let it go.  A few people exchange looks.", "info"),
    "tithe_nobody": ("With nobody in charge, nobody makes them pay.  People remember.", "bad"),
    "rest_0": ("It's the rest day.  Nobody works if they can help it.  Somebody brings out a pack of cards.", "good"),
    "rest_1": ("The rest day.  The whole place sleeps late, eats late, and spends the afternoon telling lies about the old days.", "good"),
    "rest_2": ("The rest day.  The tools stay where they are, and the kids get everyone's attention for once.", "good"),
    "door_vote_yes": ("The meeting votes on the spot, <global_val:pf_kv_dyes> to <global_val:pf_kv_dno>: they can stay.", "good"),
    "door_vote_no": ("The meeting votes on the spot, <global_val:pf_kv_dno> to <global_val:pf_kv_dyes> against.", "bad"),
    "law_passed_lord": ("So it passes, whatever the count said (<global_val:pf_kl_yes> for, <global_val:pf_kl_no> against).  From now on, <global_val:pf_kl_text>.", "good"),
    "law_failed_lord": ("So it doesn't pass, whatever the count said (<global_val:pf_kl_yes> for, <global_val:pf_kl_no> against).", "info"),
    "law_repealed_lord": ("So it goes, whatever the count said.  No more '<global_val:pf_kl_name>'.", "info"),
    "law_kept_lord": ("So the law stays, whatever the count said (<global_val:pf_kl_yes> wanted it gone, <global_val:pf_kl_no> didn't).", "info"),
    "law_lord_overrule": ("<global_val:pf_chief_name> hears the count, and overrules it.  That's what a lord is for, apparently.", "bad"),
    "law_you_overrule": ("You hear the count, and overrule it.  You're the lord; that's the job.", "info"),
    "coup": (f"Enough of them have had enough.  {CN} is pulled out of the chair, and the place goes back to choosing its own.", "bad"),
    "lord_crowned": ("<global_val:pf_kw_name> takes the chair: lord of the place now, for life.", "good"),
    "long_live": ("<global_val:pf_chief_dead_name> is gone.  <global_val:pf_heir_name> takes the chair, as was agreed.  Not everyone looks at them the same way yet.", "info"),
    "no_heir": ("<global_val:pf_chief_dead_name> is gone, and there's no heir.  It goes back to the meeting.", "bad"),
    "heir_named": (f"{CN} names <global_val:pf_heir_name> heir, in front of everyone.", "info"),
    "exile_motion": ("Somebody says what everyone has been thinking: <global_val:pf_ex_name> can't stay.", "bad"),
    "exile_yes": ("<global_val:pf_ex_yes> hands go up against <global_val:pf_ex_name>, <global_val:pf_ex_no> for.  <global_val:pf_ex_name> is put out of the place with what they can carry.", "bad"),
    "exile_no": ("It's close, but <global_val:pf_ex_name> stays, <global_val:pf_ex_no> to <global_val:pf_ex_yes>.  Nobody looks at them for the rest of the night.", "info"),
    "exile_lord_yes": (f"{CN} decides it: <global_val:pf_ex_name> goes.  They're put out with what they can carry.", "bad"),
    "exile_lord_no": (f"{CN} decides it: <global_val:pf_ex_name> stays.  For now.", "info"),
    "who_lord": (f"{CN} is lord of the place, for <global_val:pf_km_since_t> now.  Heir: <global_val:pf_km_heir>.  Next meeting: <global_val:pf_km_when>.", "info"),
    "who_you_lord": ("You're lord of the place, for <global_val:pf_km_since_t> now.  Next meeting: <global_val:pf_km_when>.", "info"),
    "law_watch_note": ("By the law of the place, everyone takes a turn.", "info"),
    "join_dark": ("<global_val:pf_tj_name> and their family are outside, but it's dark, and the law is the law.  They make camp until morning.", "info"),
})
files["lines.json"] = [eoc("PF_SAY_keep", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Keep lines, picked by the context var 'line'.")]
files["lab_keep.json"] += [
    eoc("PF_KL_law", [{"run_eocs": "PF_KEEP_count"},
                      {"if": m("pf_kp_n >= 2"), "then": [
                          {"u_location_variable": g("pf_kp_av")}, m("pf_kp_events = 0"), m("pf_kl_force = 1"), m("pf_kp_prop = 0"),
                          {"run_eocs": "PF_KEEP_law_step"}, m("pf_kl_force = 0")],
                       "else": [say("[keep lab] Fewer than 2 grown-ups who live here are in range.")]}],
        "Keep lab: somebody puts a law to a vote now (a random law not in force, or one in force to do away with; triggers ignored)."),
    eoc("PF_KL_shirk", nearest("pf_kl_s") + [
        {"if": m("pf_hl_d < 99"), "then": [m("pf_tithe_shirk = 1"), {"copy_var": g("pf_kl_s_uid"), "target_var": g("pf_tithe_shirk_uid")},
                                           {"copy_var": g("pf_kl_s_name"), "target_var": g("pf_tithe_shirk_name")}, m("pf_law_tithe = 1"),
                                           m("pf_tithe_week = value_or(pf_tithe_week, 0) + 4"),
                                           say("[keep lab] The tithe is law, and <global_val:pf_kl_s_name> has kept their share back (it comes up at the next meeting).")],
         "else": [say("[keep lab] Nobody who lives here is near.")]}]),
    eoc("PF_KL_rest", [{"run_eocs": "PF_KEEP_rest_now"}], "Keep lab: the rest day's morning, now."),
    eoc("PF_KL_laws", [m("pf_hs_a = value_or(pf_law_watch, 0)"), m("pf_hs_b = value_or(pf_law_dark, 0)"), m("pf_hs_c = value_or(pf_law_tithe, 0)"),
                       m("pf_hs_d = value_or(pf_law_rest, 0)"), m("pf_hs_e = value_or(pf_law_door, 0)"),
                       m("pf_hs_f = value_or(pf_laws_passed_total, 0)"), m("pf_hs_g = value_or(pf_laws_failed_total, 0)"), m("pf_hs_h = value_or(pf_tithe_total, 0)"),
                       say("[keep lab] laws: watch <global_val:pf_hs_a>, dark <global_val:pf_hs_b>, tithe <global_val:pf_hs_c>, rest <global_val:pf_hs_d>, door <global_val:pf_hs_e>.  Passed or repealed <global_val:pf_hs_f>, failed <global_val:pf_hs_g>, tithe so far <global_val:pf_hs_h>.")]),
]


# ============================================================ PASS 3: A LORD FOR LIFE, THE HEIR, THE COUP; EXILE
files["rule.json"] = [
    eoc("PF_KEEP_heir_step", [
        m("pf_kh_best = -999"), m("pf_kh_found = 0"),
        {"u_run_npc_eocs": [{"id": "PF_KEEP_heir_cand", "condition": {"and": [ADULT_RES, {"not": IS_CHIEF}]}, "effect": [
            {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_m_other")},
            {"run_eocs": "PF_VIEW_read", "alpha_talker": g("pf_kp_chief_t")},
            m("_s = pf_read_t + pf_read_w / 2 - pf_read_x"),
            {"if": {"or": [{"compare_string": [{"u_val": "pf_mom"}, g("pf_chief_uid")]}, {"compare_string": [{"u_val": "pf_dad"}, g("pf_chief_uid")]}]},
             "then": [m("_s += 1000")]},
            {"if": m("_s > pf_kh_best"), "then": [m("pf_kh_best = _s"), m("pf_kh_found = 1"),
                                                   {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kh_uid")}, name_into("pf_kh_name")]}]}],
         "local": True, "npc_range": 60},
        {"if": m("pf_kh_found == 1"), "then": [
            {"if": {"or": [m("value_or(pf_heir_set, 0) == 0"), {"not": {"compare_string": [g("pf_kh_uid"), g("pf_heir_uid")]}}]}, "then": [
                {"copy_var": g("pf_kh_uid"), "target_var": g("pf_heir_uid")}, {"copy_var": g("pf_kh_name"), "target_var": g("pf_heir_name")}, m("pf_heir_set = 1"),
                m("pf_kp_events += 1"), line("heir_named")]}]},
    ], "u = avatar, at a meeting with an NPC lord present: the lord names an heir: their own grown child who lives here if they have one, else whoever they think most of (their own view).  Said out loud when it changes."),
    eoc("PF_KEEP_succession", [
        m("pf_ks_ok = 0"),
        {"if": m("value_or(pf_heir_set, 0) == 1"), "then": [
            {"copy_var": g("pf_heir_uid"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
            {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_KEEP_crown", "alpha_talker": g("pf_find_who")}]}]},
        {"if": m("pf_ks_ok == 0"), "then": [m("pf_law_lord = 0"), m("pf_chief_set = 0"), m("pf_mt_due = 1"), m("pf_kp_elect = 1"), line("no_heir")]},
    ], "u = avatar.  The lord is gone (dead, or away from two meetings): the heir takes the chair if they're here and still live here; with no heir, the lordship ends and the place chooses again."),
    eoc("PF_KEEP_crown", [
        m("pf_ks_ok = 1"), m("pf_chief_set = 1"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_chief_uid")}, name_into("pf_chief_name"),
        m("pf_chief_since = time('now')"), m("pf_chief_away = 0"), m("pf_heir_set = 0"), m("pf_kp_elect = 0"),
        m("pf_successions_total = value_or(pf_successions_total, 0) + 1"),
        {"run_eocs": "PF_SAY_keep", "alpha_talker": "avatar", "variables": {"line": "long_live"}},
    ], "u = the heir: lord now.", condition={"and": [ADULT, m("value_or(u_pf_resident, 0) == 1")]}),
    # ---------------- exile
    eoc("PF_KEEP_exile_step", [
        {"if": m("time('now') - value_or(pf_ex_last, -999999) >= time('14 d')"), "then": [
            m("pf_ex_best = 0"),
            {"u_run_npc_eocs": [{"id": "PF_KEEP_ex_t", "condition": {"and": [ADULT_RES, {"not": IS_CHIEF}]}, "effect": [
                m("pf_ex_c = 0"), m("pf_ex_m = 0"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_ex_tuid")},
                {"u_run_npc_eocs": [{"id": "PF_KEEP_ex_v", "condition": {"and": [ADULT_RES, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_ex_tuid")]}}]}, "effect": [
                    {"copy_var": g("pf_ex_tuid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"}, m("pf_ex_m += 1"),
                    {"if": m("(pf_read_x >= 50) + (pf_read_w < -15) > 0"), "then": [m("pf_ex_c += 1")]}]}], "local": True, "npc_range": 60},
                {"if": m("value_or(u_pf_shirks, 0) >= 2"), "then": [m("pf_ex_c += 1")]},
                {"if": m("(pf_ex_c > pf_ex_best) * (pf_ex_c * 2 > pf_ex_m) * (pf_ex_m >= 2)"), "then": [
                    m("pf_ex_best = pf_ex_c"), m("pf_ex_n = pf_ex_m"), {"u_set_talker": g("pf_ex_who")},
                    {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_ex_uid")}, name_into("pf_ex_name")]}]}],
             "local": True, "npc_range": 60},
            {"if": m("pf_ex_best > 0"), "then": [{"run_eocs": "PF_KEEP_exile_vote"}]}]},
    ], "u = avatar.  Someone more than half the others can't stand any more (tension 50+ or warmth below -15 in their own view; keeping back the tithe twice counts against them too): the meeting votes on putting them out.  At most every 2 weeks."),
    eoc("PF_KEEP_exile_vote", [
        m("pf_kp_events += 1"), line("exile_motion"),
        m("pf_ex_yes = pf_ex_best"), m("pf_ex_no = pf_ex_n - pf_ex_best"), m("pf_ex_youv = -1"),
        {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [
            {"set_string_var": "The meeting is voting on putting <global_val:pf_ex_name> out of the place.  Do you vote to put them out?", "target_var": g("pf_ex_q"), "parse_tags": True},
            {"if": {"u_query": g("pf_ex_q"), "default": False}, "then": [m("pf_ex_yes += 1"), m("pf_ex_youv = 1")], "else": [m("pf_ex_no += 1"), m("pf_ex_youv = 0")]}]},
        m("pf_ex_pass = pf_ex_yes > pf_ex_no"),
        {"if": {'math': ['value_or(pf_law_lord, 0) == 1']}, "then": [
            {"if": m("(value_or(pf_chief_set, 0) == 2) * (pf_ex_youv >= 0)"), "then": [m("pf_ex_pass = pf_ex_youv"), m("pf_ex_bylord = 1")]},
            {"if": m("value_or(pf_chief_set, 0) == 1"), "then": [
                {"copy_var": g("pf_ex_uid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read", "alpha_talker": g("pf_kp_chief_t")},
                m("pf_ex_pass = (pf_read_x >= 40) + (pf_read_w < -10) > 0"), m("pf_ex_bylord = 2")]}]},
        {"if": m("pf_ex_pass == 1"),
         "then": [{"if": m("value_or(pf_ex_bylord, 0) == 2"), "then": [line("exile_lord_yes")], "else": [line("exile_yes")]},
                  {"run_eocs": "PF_KEEP_exile_do", "alpha_talker": g("pf_ex_who")}],
         "else": [{"if": m("value_or(pf_ex_bylord, 0) == 2"), "then": [line("exile_lord_no")], "else": [line("exile_no")]}]},
        m("pf_ex_bylord = 0"), m("pf_ex_last = time('now')"),
    ], "u = avatar.  The vote: everyone who can't stand them is for, the rest against, and you (a popup).  Under a lord, the lord decides (from their own view: tension 40+ or warmth below -10); if you're the lord, your vote decides."),
    eoc("PF_KEEP_exile_do", [
        m("u_pf_resident = 0"), m("u_pf_role = 0"), m("u_pf_exiled = 1"), m("pf_residents_n = max(value_or(pf_residents_n, 1) - 1, 0)"),
        {"if": {"and": [m("value_or(pf_heir_set, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_heir_uid")]}]}, "then": [m("pf_heir_set = 0")]},
        {"if": IS_COUNCIL, "then": [m("pf_cn_n = 0"), m("pf_mt_due = 1")]},
        {"if": m("value_or(pf_chief_set, 0) == 2"), "then": [{"set_string_var": "AVATAR", "target_var": g("pf_m_other")}],
         "else": [{"copy_var": g("pf_chief_uid"), "target_var": g("pf_m_other")}]},
        {"if": m("value_or(pf_chief_set, 0) > 0"), "then": [m("pf_mv_role = 1"), m("pf_m_str_in = 90"), {"run_eocs": "PF_MV_ruled_against"}]},
        {"if": {"u_has_trait": "PF_AGENT"},
         "then": [{"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_band_new_leader")}, {"run_eocs": "PF_ALIFE_register_band"},
                  m("pf_ws_task = 1"), m("pf_ws_kind = 0"), {"run_eocs": "PF_WORLD_init_leader"}],
         "else": [{"u_location_variable": {"u_val": "pf_walk_to"}},
                  {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("(rand(1) * 2 - 1) * 50"), "y_adjust": m("rand(40) - 20")},
                  {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]},
        m("pf_exiles_total = value_or(pf_exiles_total, 0) + 1"),
    ], "u = the exile: no longer lives here (no job, no home), resents the chief (ruled_against, strong), and walks away: an A-Life person becomes a band of one out there, anyone else just goes.  If they were the heir, there's no heir now."),
]
files["lab_keep.json"] += [
    eoc("PF_KL_lord", [{"if": m("value_or(pf_chief_set, 0) > 0"), "then": [m("pf_law_lord = 1"), m("pf_law_lord_t = time('now')"), say("[keep lab] The chief is lord for life now (the law is in force).")],
                        "else": [say("[keep lab] There's no chief to make lord.")]}]),
    eoc("PF_KL_succeed", [{"if": {"and": [m("value_or(pf_law_lord, 0) == 1"), m("value_or(pf_chief_set, 0) == 1")]}, "then": [
        {"copy_var": g("pf_chief_uid"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
        {"if": m("pf_find_ok == 1"), "then": [{"copy_var": g("pf_find_who"), "target_var": g("pf_kp_chief_t")}, m("pf_kp_events = 0"), {"run_eocs": "PF_KEEP_heir_step"},
                                               {"copy_var": g("pf_chief_name"), "target_var": g("pf_chief_dead_name")}, {"run_eocs": "PF_KEEP_succession"}],
         "else": [say("[keep lab] The lord isn't here.")]}],
        "else": [say("[keep lab] There's no NPC lord.")]}],
        "Keep lab: the lord names an heir, then hands over the chair as if they had died (they don't)."),
    eoc("PF_KL_outcast", nearest("pf_kl_o") + [
        {"if": m("pf_hl_d < 99"), "then": [
            {"u_run_npc_eocs": [{"id": "PF_KL_shun", "condition": {"and": [ADULT_RES, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kl_o_uid")]}}]}, "effect": [
                {"copy_var": g("pf_kl_o_uid"), "target_var": g("pf_m_other")}, m("pf_mv_role = 1"), m("pf_m_str_in = 90"), {"run_eocs": "PF_MV_betrayal"}]}],
             "local": True, "npc_range": 60},
            m("pf_ex_last = -999999"),
            say("[keep lab] Everyone who lives here now feels betrayed by <global_val:pf_kl_o_name>: the next meeting votes on putting them out.")],
         "else": [say("[keep lab] Nobody who lives here is near (not the chief).")]}]),
    eoc("PF_KL_rule", [m("pf_hs_a = value_or(pf_law_lord, 0)"), m("pf_hs_b = value_or(pf_heir_set, 0)"), m("pf_hs_c = value_or(pf_successions_total, 0)"),
                       m("pf_hs_d = value_or(pf_coups_total, 0)"), m("pf_hs_e = value_or(pf_exiles_total, 0)"),
                       say("[keep lab] lord law <global_val:pf_hs_a>, chief <global_val:pf_chief_name>, heir set <global_val:pf_hs_b> (<global_val:pf_heir_name>), successions <global_val:pf_hs_c>, coups <global_val:pf_hs_d>, exiles <global_val:pf_hs_e>.")]),
]


# ============================================================ PASS 4: THE WALL AND THE SIEGE
WALL_R = 12                                   # the wall: a square palisade WALL_R tiles out from home
GROUND = ["t_grass", "t_grass_long", "t_grass_dead", "t_grass_tall", "t_grass_golf", "t_grass_white", "t_dirt", "t_underbrush", "t_moss", "t_sand"]
REST_OFF = f"(value_or(pf_law_rest, 0) == 1) * ({TODAY} % 7 == {MEET_DAY}) == 0"
SIDES = {1: ("north", -WALL_R, -WALL_R, 1, 0), 2: ("east", WALL_R, -WALL_R, 0, 1), 3: ("south", WALL_R, WALL_R, -1, 0), 4: ("west", -WALL_R, WALL_R, 0, -1)}
# (axis: 0 = the side runs east-west, 1 = north-south; offset of the line from home; inward step)
SIDE_LINE = {1: (0, -WALL_R, 0, 1), 2: (1, WALL_R, -1, 0), 3: (0, WALL_R, 0, -1), 4: (1, -WALL_R, 1, 0)}
DIRS = {0: ("north", 0, -1), 1: ("east", 1, 0), 2: ("south", 0, 1), 3: ("west", -1, 0)}
WAVES = {1: [("mon_zombie", "pf_sg_n")],
         2: [("mon_zombie", "max(pf_sg_n - 3, 1)"), ("mon_zombie_runner", "2"), ("mon_zombie_dog", "2")],
         3: [("mon_zombie", "max(pf_sg_n - 4, 1)"), ("mon_zombie_tough", "2"), ("mon_zombie_fat", "1"), ("mon_zombie_brute", "1")]}
side_start = [{"if": m(f"pf_wl_side == {k}"), "then": [
    {"copy_var": g("pf_home_loc"), "target_var": g("pf_wl_at")},
    {"location_variable_adjust": g("pf_wl_at"), "x_adjust": x0, "y_adjust": y0},
    m(f"pf_wl_dx = {dx}"), m(f"pf_wl_dy = {dy}"), {"set_string_var": nm, "target_var": g("pf_wl_name")},
    m(f"pf_wl_ax = {SIDE_LINE[k][0]}"), m(f"pf_wl_off = {SIDE_LINE[k][1]}"), m(f"pf_wl_ix = {SIDE_LINE[k][2]}"), m(f"pf_wl_iy = {SIDE_LINE[k][3]}")]}
    for k, (nm, x0, y0, dx, dy) in SIDES.items()]
# is u standing on (or right next to) the line this side goes up on?  (u_pf_pos must be fresh)
ON_LINE = (f"((pf_wl_ax == 0) * (abs(u_pf_pos.y - pf_home_loc.y - pf_wl_off) <= 0) * (abs(u_pf_pos.x - pf_home_loc.x) <= {WALL_R})"
           f" + (pf_wl_ax == 1) * (abs(u_pf_pos.x - pf_home_loc.x - pf_wl_off) <= 0) * (abs(u_pf_pos.y - pf_home_loc.y) <= {WALL_R})) > 0")
def step_off(sign):
    """Effects (u = someone on the line): moved 2 tiles inward (sign 1) or outward (sign -1), cheaply, inside the bubble."""
    return [{"copy_var": {"u_val": "pf_pos"}, "target_var": {"u_val": "pf_tp"}},
            {"location_variable_adjust": {"u_val": "pf_tp"}, "x_adjust": m(f"pf_wl_ix * 2 * {sign}"), "y_adjust": m(f"pf_wl_iy * 2 * {sign}")},
            {"u_teleport": {"u_val": "pf_tp"}, "force_safe": True}, m("pf_wl_moved += 1")]
wave_spawn = []
for w, mons in WAVES.items():
    eff = []
    for mon, n in mons:
        eff.append({"u_spawn_monster": mon, "real_count": {"math": [n]}, "target_var": g("pf_sg_at"), "min_radius": 0, "max_radius": 6})
    wave_spawn.append({"if": m(f"pf_sg_wave == {w}"), "then": eff})
dir_set = [{"if": m(f"pf_sg_dir == {d}"), "then": [{"set_string_var": nm, "target_var": g("pf_sg_dirname")}, m(f"pf_sg_dx = {dx}"), m(f"pf_sg_dy = {dy}")]}
           for d, (nm, dx, dy) in DIRS.items()]
files["walls.json"] = [
    {"type": "ter_furn_transform", "id": "PF_KEEP_t_wall", "terrain": [{"result": "t_palisade", "valid_terrain": GROUND}]},
    # the gates are wooden privacy gates: a real door anyone can open by hand (the palisade gate needs a rope-and-pulley rig on
    # the wall to open, so a gate shut for the night would have locked people in or out).  Old palisade gates are converted.
    {"type": "ter_furn_transform", "id": "PF_KEEP_t_gate", "terrain": [{"result": "t_privacy_fencegate_o", "valid_terrain": GROUND}]},
    {"type": "ter_furn_transform", "id": "PF_KEEP_t_shut", "terrain": [{"result": "t_privacy_fencegate_c", "valid_terrain": ["t_privacy_fencegate_o", "t_palisade_gate_o", "t_palisade_gate"]}]},
    {"type": "ter_furn_transform", "id": "PF_KEEP_t_open", "terrain": [{"result": "t_privacy_fencegate_o", "valid_terrain": ["t_privacy_fencegate_c", "t_palisade_gate", "t_palisade_gate_o"]}]},
    {"type": "morale_type", "id": "PF_morale_held", "text": "The place held"},
    eoc("PF_KEEP_wall_start", [
        m("pf_wall_state = 1"), m("pf_wall_side = 0"), line("wall_start"),
    ], "u = avatar.  Home menu: Build a wall around the place.  From the next morning, one side a day (north, east, south, west), a gate in each.",
        condition={"and": [m(AT_HOME), m("value_or(pf_wall_state, 0) == 0")]}),
    eoc("PF_KEEP_wall_tick", [
        m(f"pf_wall_day = {TODAY}"),
        {"u_location_variable": g("pf_kp_av")},
        {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [{"run_eocs": "PF_KEEP_count"},
            {"if": m("pf_kp_n >= 2"), "then": [{"run_eocs": "PF_KEEP_wall_side"}]}]},
    ], "Once a day, 08:00-12:00, while the wall is going up and you're home (the map is loaded) with 2+ grown-ups living here: the next side goes up.  Not on the rest day.",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_wall_state, 0) == 1"), m(f"{HOUR} >= 8"), m(f"{HOUR} < 12"),
                           m(f"value_or(pf_wall_day, -1) != {TODAY}"), m(REST_OFF)]}),
    eoc("PF_KEEP_wall_side", [
        m("pf_wall_side = value_or(pf_wall_side, 0) + 1"), m("pf_wl_side = pf_wall_side"),
    ] + side_start + [
        # nobody gets walled in: people on the line step inward, monsters are pushed outward, before a log goes up
        m("pf_wl_moved = 0"),
        {"u_run_npc_eocs": [{"id": "PF_KEEP_wall_clear_npc", "effect": [{"u_location_variable": {"u_val": "pf_pos"}}, {"if": m(ON_LINE), "then": step_off(1)}]}],
         "local": True, "npc_range": 60},
        {"run_eocs": {"id": "PF_KEEP_wall_clear_you", "effect": [{"u_location_variable": {"u_val": "pf_pos"}}, {"if": m(ON_LINE), "then": step_off(1)}]},
         "alpha_talker": "avatar"},
        {"u_run_monster_eocs": [{"id": "PF_KEEP_wall_clear_mon", "effect": [{"u_location_variable": {"u_val": "pf_pos"}}, {"if": m(ON_LINE), "then": step_off(-1)}]}],
         "monster_range": 60},
        m("pf_wl_i = 0"),
        {"run_eocs": "PF_KEEP_wall_tile", "condition": m(f"pf_wl_i < {2 * WALL_R}"), "iterations": 2 * WALL_R + 2},
        m("pf_tw_role = 4"), {"run_eocs": "PF_TOWN_worker"},
        {"if": m("pf_tw_wbest < 100"), "then": [m("pf_tw_role = 8"), {"run_eocs": "PF_TOWN_worker"}]},
        {"if": m("pf_wall_side >= 4"),
         "then": [m("pf_wall_state = 2"), m("pf_wall_done_t = time('now')"),
                  {"u_add_morale": "PF_morale_held", "bonus": 6, "max_bonus": 6, "duration": "1 days", "decay_start": "12 hours"},
                  {"if": m("value_or(pf_town_named, 0) == 1"), "then": [{"copy_var": g("pf_town_name"), "target_var": g("pf_kp_place")}, {"copy_var": g("pf_town_name"), "target_var": g("pf_kp_Place")}],
                   "else": [{"set_string_var": "the place", "target_var": g("pf_kp_place")}, {"set_string_var": "The place", "target_var": g("pf_kp_Place")}]},
                  line("wall_done")],
         "else": [{"if": m("value_or(pf_aw_quiet, 0) == 0"), "then": [{"if": m("pf_tw_wbest >= 0"), "then": [line("wall_side")], "else": [line("wall_side_you")]}]}]},
    ], "u = avatar.  One side of the wall.  First, nobody is walled in: anyone standing on the line (people, you included) steps 2 tiles inward, and any monster on it is pushed 2 tiles outward (an in-bubble teleport, same turn).  Then a palisade over open ground (grass, dirt, brush; never buildings, roads or the field), a gate in the middle.  The tinkerer (or the smith, or whoever's most able) leads the work."),
    eoc("PF_KEEP_wall_tile", [
        {"if": m(f"pf_wl_i == {WALL_R}"),
         "then": [{"u_transform_radius": 0, "ter_furn_transform": "PF_KEEP_t_gate", "target_var": g("pf_wl_at")}],
         "else": [{"u_transform_radius": 0, "ter_furn_transform": "PF_KEEP_t_wall", "target_var": g("pf_wl_at")}]},
        {"location_variable_adjust": g("pf_wl_at"), "x_adjust": m("pf_wl_dx"), "y_adjust": m("pf_wl_dy")},
        m("pf_wl_i += 1"),
    ], "u = avatar.  One tile of the wall (the middle one is a gate), then a step along the side."),
    eoc("PF_KEEP_gates_tick", [
        m(f"pf_gt_night = (({HOUR} >= 22) + ({HOUR} < 6)) > 0"),
        {"if": m("value_or(pf_gates_v2, 0) == 0"), "then": [m("pf_gates_v2 = 1"), m("pf_gates_shut = -1")]},
        {"u_location_variable": g("pf_kp_av")},
        {"if": m("(distance(pf_kp_av, pf_home_loc) <= 40) * (pf_gt_night != value_or(pf_gates_shut, 0))"), "then": [
            {"if": m("pf_gt_night == 1"),
             "then": [{"u_transform_radius": WALL_R + 1, "ter_furn_transform": "PF_KEEP_t_shut", "target_var": g("pf_home_loc")}, m("pf_gates_shut = 1"),
                      # full run day 98: back home at 05:53, "pulled shut for the night" minutes before they opened; only
                      # said at nightfall (catching up later shuts them quietly)
                      {"if": {"and": [m(CALM), m(f"{HOUR} >= 22")]}, "then": [line("gates_shut")]}],
             "else": [{"u_transform_radius": WALL_R + 1, "ter_furn_transform": "PF_KEEP_t_open", "target_var": g("pf_home_loc")}, m("pf_gates_shut = 0")]}]},
    ], "Every 30 minutes with a wall: the gates are shut at 22:00 and opened at 06:00 (when you're home, so the map is loaded).  They're wooden privacy gates: anyone can open one to go through.  The first run converts old palisade gates (which need a pulley to open).",
        recurrence="30 minutes", **{"global": True}, condition={"and": [m(AT_HOME), m("value_or(pf_wall_state, 0) >= 1")]}),
]
files["siege.json"] = [
    eoc("PF_SIEGE_tick", [
        m(f"pf_sg_check = {TODAY}"),
        {"if": m("has_var(pf_sg_first_day) == 0"), "then": [m(f"pf_sg_first_day = {TODAY}")]},
        {"if": m(f"{TODAY} - value_or(pf_sg_last_day, pf_sg_first_day) >= 21"), "then": [
            {"u_location_variable": g("pf_kp_av")},
            {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [{"run_eocs": "PF_KEEP_count"},
                {"if": m("(pf_kp_n >= 4) * (rand(4) == 0)"), "then": [{"run_eocs": "PF_SIEGE_warn"}]}]}]},
    ], "Once a day around noon, when you're home: once the place has 4+ grown-ups and it's been 3 weeks since the last siege (or since the first time it was checked), one day in five a horde turns toward it.  Word comes a day ahead.",
        recurrence="1 hours", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_alife_on, 1) == 1"), m(f"{HOUR} >= 12"), m(f"{HOUR} < 13"), m(f"value_or(pf_sg_check, -1) != {TODAY}"),
                           m("value_or(pf_sg_state, 0) == 0")]}),
    eoc("PF_SIEGE_warn", [
        m("pf_sg_state = 1"), m(f"pf_sg_day = {TODAY} + 1"), m("pf_sg_dir = rand(3)"), m("pf_sg_wave = 0"), m("pf_sg_delays = 0"),
    ] + dir_set + [line("siege_warn")], "u = avatar.  A horde is coming from one direction, tomorrow night."),
    eoc("PF_SIEGE_night", [
        {"u_location_variable": g("pf_kp_av")},
        {"if": m("distance(pf_kp_av, pf_home_loc) > 40"), "then": [
            {"if": m("pf_sg_wave == 0"), "then": [
                m("pf_sg_delays += 1"),
                {"if": m("pf_sg_delays >= 3"), "then": [m("pf_sg_state = 0"), m(f"pf_sg_last_day = {TODAY}"), line("siege_passes")],
                 "else": [m(f"pf_sg_day = {TODAY} + 1")]}]}],
         "else": [
            {"if": m("pf_sg_wave == 0"), "then": [m("pf_sg_t0 = time('now')"), m("pf_sg_deaths0 = value_or(pf_ours_dead_total, 0)"), m("pf_sg_guest_dead = 0"), m("pf_sg_n = clamp(4 + value_or(pf_residents_n, 0) / 2, 4, 12)")]},
            {"if": m("(pf_sg_wave < 3) * (time('now') - pf_sg_t0 >= time('40 m') * pf_sg_wave)"), "then": [{"run_eocs": "PF_SIEGE_wave"}]},
            {"if": m("pf_sg_wave >= 1"), "then": [{"u_make_sound": "the place, carrying on the night air", "volume": 50, "type": "activity", "target_var": g("pf_home_loc")}]},
            {"if": m("(pf_sg_wave >= 3) * (time('now') - pf_sg_t0 >= time('2 h'))"), "then": [
                {"run_eocs": "PF_THREAT_scan"},
                {"if": {"or": [m("(pf_threat == 0) * (value_or(pf_horn_active, 0) == 0)"), m("time('now') - pf_sg_t0 >= time('4 h')")]}, "then": [{"run_eocs": "PF_SIEGE_end"}]}]}]},
    ], "Every 10 minutes on the night of the siege (from 21:00): if you're away, the horde is delayed (three times, then it passes by).  If you're home: three waves 40 minutes apart from the warned direction, the place's noise drawing them in (the watch, the Horn and the defense patches do the fighting).  Once it's calm again (2 hours in at least, 4 at most), the tally.",
        recurrence="10 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_sg_state, 0) == 1"), m(f"{TODAY} >= value_or(pf_sg_day, 999999)"), {"or": [m(f"{HOUR} >= 21"), m(f"{HOUR} < 5"), m("pf_sg_wave > 0")]}]}),
    eoc("PF_SIEGE_wave", [
        m("pf_sg_wave += 1"), m("pf_sg_waves_total = value_or(pf_sg_waves_total, 0) + 1"),
        {"if": m("value_or(pf_st_allied, 0) == 1"), "then": [m("pf_sg_n = max(pf_sg_n - 2, 3)"), line("siege_allies")]},
    ] + dir_set + [
        {"copy_var": g("pf_home_loc"), "target_var": g("pf_sg_at")},
        {"location_variable_adjust": g("pf_sg_at"), "x_adjust": m("pf_sg_dx * 35 + rand(10) - 5"), "y_adjust": m("pf_sg_dy * 35 + rand(10) - 5")},
    ] + wave_spawn + [
        {"if": m("pf_sg_wave == 1"), "then": [line("siege_wave1"),
            # full run day 122: the household held the posts and the children (and Dante) were alone inside when the windows broke.
            # One grown-up, a parent first, stays in with the children for the night; the Horn leaves them there.
            m("pf_sg_kids = 0"), m("pf_sg_ad = 0"), m("pf_sg_kbest = -1"),
            {"u_run_npc_eocs": [{"id": "PF_SIEGE_kidcount", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, m("value_or(u_pf_resident, 0) == 1")]},
                                 "effect": [m("pf_sg_kids += 1")]}], "local": True, "npc_range": 60},
            {"u_run_npc_eocs": [{"id": "PF_SIEGE_keeper_pick", "condition": {"and": [ADULT_RES, {"not": {"u_has_effect": "sleep"}}]}, "effect": [
                m("pf_sg_ad += 1"), m("_ks = value_or(u_pf_kids_n, 0) * 10 + rand(5)"),
                {"if": m("_ks > pf_sg_kbest"), "then": [m("pf_sg_kbest = _ks"), {"u_set_talker": g("pf_sg_keeper")}]}]}], "local": True, "npc_range": 60},
            {"if": m("(pf_sg_kids > 0) * (pf_sg_ad >= 2) * (pf_sg_kbest >= 0)"), "then": [
                {"run_eocs": {"id": "PF_SIEGE_keeper_set", "effect": [
                    m("u_pf_sg_keep_t = pf_sg_t0"), name_into("pf_say_a"),
                    {"copy_var": g("pf_home_loc"), "target_var": {"u_val": "pf_walk_to"}},
                    {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]}, "alpha_talker": g("pf_sg_keeper")},
                line("siege_keeper")]}]},
        # full run day 99: Dante slept through the whole siege (two of his people died); the first wave wakes you
        {"if": {"and": [m("pf_sg_wave == 1"), {"u_has_effect": "sleep"}]}, "then": [
            {"u_lose_effect": "sleep"}, {"u_lose_effect": "lying_down"}, {"u_lose_effect": "PF_sleep_easy"}, line("siege_wake")]},
        {"if": m("pf_sg_wave == 2"), "then": [line("siege_wave2")]},
        {"if": m("pf_sg_wave == 3"), "then": [line("siege_wave3")]},
    ], "u = avatar.  A wave, 35 tiles out in the warned direction: the dead (wave 1), with runners and dogs (wave 2), with the tough ones and a brute (wave 3).  Size grows with the place."),
    eoc("PF_SIEGE_end", [
        m("pf_sg_state = 0"), m(f"pf_sg_last_day = {TODAY}"), m("pf_sg_lost = value_or(pf_ours_dead_total, 0) - pf_sg_deaths0"),
        m("pf_sieges_total = value_or(pf_sieges_total, 0) + 1"), m("pf_sieges_held = value_or(pf_sieges_held, 0) + 1"),
        m(f"pf_sg_retell_day = {TODAY} + 1"),
        {"u_add_morale": "PF_morale_held", "bonus": 10, "max_bonus": 10, "duration": "2 days", "decay_start": "1 days"},
        {"u_run_npc_eocs": [{"id": "PF_SIEGE_bond", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), m("has_var(u_pf_uid)")]},
                             "effect": [m("pf_m_str_in = 60"), {"run_eocs": "PF_MK_shared_danger", "beta_talker": "avatar"}]}], "local": True, "npc_range": 60},
        {"if": m("value_or(pf_town_named, 0) == 1"), "then": [{"copy_var": g("pf_town_name"), "target_var": g("pf_kp_place")}, {"copy_var": g("pf_town_name"), "target_var": g("pf_kp_Place")}],
                   "else": [{"set_string_var": "the place", "target_var": g("pf_kp_place")}, {"set_string_var": "The place", "target_var": g("pf_kp_Place")}]},
        {"if": m("pf_sg_lost == 0"), "then": [line("siege_held")], "else": [line("siege_held_loss")]},
        # full run day 157: Nyla Reedy (a band camped by the gate) fought on the wall and died; the dawn said "every one of you
        # is still standing".  Someone who wasn't yours and fell defending the place is named.
        {"if": m("value_or(pf_sg_guest_dead, 0) == 1"), "then": [line("siege_guest_fell")]},
        {"if": m("value_or(pf_sg_guest_dead, 0) > 1"), "then": [line("siege_guests_fell")]},
    ], "u = avatar.  The siege is over: who was lost, 'The place held' morale (+10), a shared-danger moment between you and everyone who lives here, and the place's draw goes up (a place that held gets talked about)."),
    eoc("PF_SIEGE_guest_died", [m("pf_sg_guest_dead = value_or(pf_sg_guest_dead, 0) + 1"),
                                  {"set_string_var": "<u_name>", "target_var": g("pf_sg_guest_name"), "parse_tags": True}],
        "Signal: someone who doesn't live here (a visiting band, a neighbor) dies while the siege is on, at the place.",
        condition={"and": ["has_alpha", "u_is_npc", m("has_var(u_pf_uid)"), m("value_or(pf_sg_state, 0) == 1"), m("value_or(pf_sg_wave, 0) >= 1"),
                           m("value_or(u_pf_resident, 0) == 0"), m("value_or(u_pf_envoy, 0) == 0"), m("value_or(u_pf_nv_gone, 0) == 0")]},
        eoc_type="EVENT", required_event="character_dies"),
    eoc("PF_SIEGE_retell_tick", [
        m("pf_sg_retell_day = -1"),
        {"if": m(CALM), "then": [{"if": m("pf_sg_lost == 0"), "then": [line("siege_retell")], "else": [line("siege_retell_loss")]}]},
    ], "The evening after a siege, at the fire or the table: it's told again.", recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m(f"value_or(pf_sg_retell_day, -1) == {TODAY}"), m(f"{HOUR} >= 20"), m(f"{HOUR} < 23")]}),
]
LINES.update({
    "siege_keeper": ("<global_val:pf_say_a> stays inside with the children, back to the wall, facing the door.  \"Nobody gets past me.  Go.\"", "info"),
    "wall_start": ("You put it to everyone: a wall, all the way round.  Starting tomorrow morning, a side a day.", "info"),
    "wall_side": ("<global_val:pf_say_a> leads the work on the <global_val:pf_wl_name> wall.  By noon there's a line of sharpened logs where there was grass, and a gate in the middle.", "good"),
    "wall_side_you": ("You put up the <global_val:pf_wl_name> wall yourselves, log by log, with a gate in the middle.", "good"),
    "wall_done": ("The last side goes up.  <global_val:pf_kp_Place> has a wall now, all the way round.  People keep walking along it, touching it.", "good"),
    "gates_shut": ("The gates are pulled shut for the night.", "info"),
    "siege_warn": ("A neighbor comes running, out of breath: a horde is moving this way, out of the <global_val:pf_sg_dirname>.  It'll be here tomorrow night.", "bad"),
    "siege_passes": ("The horde turned aside while you were away.  Nobody's sorry.", "info"),
    "siege_wave1": ("Out of the <global_val:pf_sg_dirname>, in the dark: the first of them.  Then more.  Then too many to count.", "bad"),
    "siege_wake": ("Hands on you in the dark, shaking.  \"Up.  They're here, all of them.  It's tonight.\"", "bad"),
    "siege_wave2": ("A second wave comes out of the <global_val:pf_sg_dirname>, faster this time: runners, and dogs that used to be dogs.", "bad"),
    "siege_wave3": ("The last wave: the big ones, the ones that don't go down.", "bad"),
    "siege_held": ("It's over.  The dead lie in heaps at the foot of the wall, and every one of you is still standing.  <global_val:pf_kp_Place> held.", "good"),
    "siege_guest_fell": ("<global_val:pf_sg_guest_name> wasn't one of yours, and fought at the wall anyway.  They didn't get up again.", "bad"),
    "siege_guests_fell": ("<global_val:pf_sg_guest_dead> who weren't yours fought at the wall anyway, and didn't get up again.  The last of them was <global_val:pf_sg_guest_name>.", "bad"),
    "siege_held_loss": ("It's over.  <global_val:pf_kp_Place> held, but <global_val:pf_sg_lost> of yours didn't live to see it.", "bad"),
    "siege_retell": ("At the fire, the siege gets told again.  It's already bigger than it was.  Nobody minds.", "good"),
    "siege_retell_loss": ("At the fire, they tell the siege again, and then they say the names of the ones who didn't make it.", "info"),
})
files["lines.json"] = [eoc("PF_SAY_keep", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Keep lines, picked by the context var 'line'.")]
files["lab_keep.json"] += [
    eoc("PF_KL_wall_side", [{"if": m("value_or(pf_wall_state, 0) == 0"), "then": [m("pf_wall_state = 1"), m("pf_wall_side = 0")]},
                            {"if": m("pf_wall_state == 1"), "then": [{"run_eocs": "PF_KEEP_wall_side"}, say("[keep lab] Side <global_val:pf_wall_side> (<global_val:pf_wl_name>) built; <global_val:pf_wl_moved> moved off the line.")],
                             "else": [say("[keep lab] The wall is finished.")]}],
        "Keep lab: the next side of the wall goes up now."),
    eoc("PF_KL_wall_redo", [
        {"if": m("value_or(pf_wall_state, 0) == 0"), "then": [say("[keep lab] There's no wall.")], "else": [
            {"u_location_variable": g("pf_kl_wpos")},
            m("_x = pf_kl_wpos.x - pf_home_loc.x"), m("_y = pf_kl_wpos.y - pf_home_loc.y"),
            m("_s = abs(_y) >= abs(_x) ? (_y < 0 ? 1 : 3) : (_x > 0 ? 2 : 4)"),
            m("pf_kl_wstate = pf_wall_state"), m("pf_kl_wside = pf_wall_side"),
            m("pf_wall_state = 1"), m("pf_wall_side = _s - 1"), {"run_eocs": "PF_KEEP_wall_side"},
            m("pf_wall_state = pf_kl_wstate"), m("pf_wall_side = pf_kl_wside"),
            say("[keep lab] Rebuilt the <global_val:pf_wl_name> side; <global_val:pf_wl_moved> moved off the line.")]}],
        "Keep lab: the side of the wall nearest you goes up again (walls where it's open ground again; anyone on the line steps off first)."),
    eoc("PF_KL_siege_warn", [m("pf_sg_state = 0"), {"run_eocs": "PF_SIEGE_warn"}, m(f"pf_sg_day = {TODAY}"),
                             say("[keep lab] The horde comes tonight (from 21:00).")]),
    eoc("PF_KL_siege_wave", [{"if": m("value_or(pf_sg_state, 0) == 1"), "then": [
        {"if": m("pf_sg_wave == 0"), "then": [m("pf_sg_t0 = time('now')"), m("pf_sg_deaths0 = value_or(pf_ours_dead_total, 0)"), m("pf_sg_guest_dead = 0"), m("pf_sg_n = clamp(4 + value_or(pf_residents_n, 0) / 2, 4, 12)")]},
        m(f"pf_sg_day = {TODAY}"), m("pf_sg_t0 = time('now') - time('40 m') * pf_sg_wave"), {"run_eocs": "PF_SIEGE_wave"}],
        "else": [say("[keep lab] No horde is coming (use the warning first).")]}],
        "Keep lab: the next wave now (it counts as the siege night)."),
    eoc("PF_KL_siege_end", [{"if": m("value_or(pf_sg_state, 0) == 1"), "then": [{"run_eocs": "PF_SIEGE_end"}], "else": [say("[keep lab] There's no siege.")]}]),
    eoc("PF_KL_walls", [m("pf_hs_a = value_or(pf_wall_state, 0)"), m("pf_hs_b = value_or(pf_wall_side, 0)"), m("pf_hs_c = value_or(pf_sg_state, 0)"),
                        m("pf_hs_d = value_or(pf_sg_wave, 0)"), m("pf_hs_e = value_or(pf_sieges_held, 0)"),
                        say("[keep lab] wall state <global_val:pf_hs_a> (0 none, 1 going up, 2 done), sides <global_val:pf_hs_b>, siege state <global_val:pf_hs_c>, wave <global_val:pf_hs_d>, sieges held <global_val:pf_hs_e>.")]),
]


# ============================================================ PASS 5: THE NEIGHBORS (rival settlements)
# Up to three settlements out there, as data (no population is spawned): a feudal keep, the "eyeglasses" bureaucrats
# and the woodlanders.  Envoys, pacts, tribute and raids; the ruler decides (you if you're chief or there's none).
NB_MAX = 3
KINDS = {0: ("keep", "a fortified keep under a lord", ["the Ridge Keep", "Stonegate", "Fort Halloran", "Castle Burke"], ["Lord", "Lady"], -10),
         1: ("eyeglasses", "an office of the old government's survivors, all clipboards and ration cards", ["the Office of Continuity", "Relief Station Nine", "the Registry", "District Four Administration"], ["Administrator", "Deputy Director"], 0),
         2: ("woodlanders", "forest folk, who keep to the trees and trade fair", ["the Pines", "Hollow Oak", "the Fern Camp", "Cedar Run"], ["old", "young"], 10)}
SURNAMES = ["Halloran", "Pike", "Maren", "Voss", "Abernathy", "Quill", "Okafor", "Lindqvist", "Ferro", "Hale"]
DIRS8 = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
NUMF = ["kind", "rel", "pact", "trib", "str", "raid", "kin"]   # kin (pass 6): family by marriage
STRF = ["name", "lead", "dir"]
def nb_ref(field, ctxname):
    return {"set_string_var": f"pf_st_{field}_<global_val:pf_st_i>", "target_var": ctx(ctxname), "parse_tags": True}
def RAID_NOISE(desc):
    return {"u_make_sound": desc, "volume": 40, "type": "alert", "target_var": g("pf_stores_loc")}
NB_LOAD = []
for f in NUMF:
    NB_LOAD += [nb_ref(f, "r" + f), m(f"pf_cur_{f} = value_or(v_r{f}, 0)")]
for f in STRF:
    NB_LOAD += [nb_ref(f, "r" + f), {"copy_var": {"var_val": "r" + f}, "target_var": g(f"pf_cur_{f}")}]
NB_STORE = []
for f in NUMF:
    NB_STORE += [nb_ref(f, "w" + f), m(f"v_w{f} = pf_cur_{f}")]
for f in STRF:
    NB_STORE += [nb_ref(f, "w" + f), {"copy_var": g(f"pf_cur_{f}"), "target_var": {"var_val": "w" + f}}]
REL_WORD = [{"if": m("pf_cur_rel <= -30"), "then": [{"set_string_var": "hostile", "target_var": g("pf_cur_relw")}]},
            {"if": m("(pf_cur_rel > -30) * (pf_cur_rel < 0)"), "then": [{"set_string_var": "wary", "target_var": g("pf_cur_relw")}]},
            {"if": m("(pf_cur_rel >= 0) * (pf_cur_rel < 30)"), "then": [{"set_string_var": "neutral", "target_var": g("pf_cur_relw")}]},
            {"if": m("(pf_cur_rel >= 30) * (pf_cur_rel < 60)"), "then": [{"set_string_var": "friendly", "target_var": g("pf_cur_relw")}]},
            {"if": m("pf_cur_rel >= 60"), "then": [{"set_string_var": "close allies", "target_var": g("pf_cur_relw")}]}]
PACT_WORD = [{"if": m("pf_cur_pact == 0"), "then": [{"if": m("pf_cur_trib == 1"), "then": [{"set_string_var": "you pay them tribute", "target_var": g("pf_cur_pactw")}],
                                                     "else": [{"set_string_var": "no agreement", "target_var": g("pf_cur_pactw")}]}]},
             {"if": m("pf_cur_pact == 1"), "then": [{"set_string_var": "a trade agreement", "target_var": g("pf_cur_pactw")}]},
             {"if": m("pf_cur_pact == 2"), "then": [{"set_string_var": "a pact to stand together", "target_var": g("pf_cur_pactw")}]},
             {"if": m("pf_cur_kin == 1"), "then": [{"set_string_var": "<global_val:pf_cur_pactw>, and family by marriage", "target_var": g("pf_cur_pactw"), "parse_tags": True}]}]
KIND_SET = []
for kd, (key, desc, names, titles, rel0) in KINDS.items():
    eff = [m(f"pf_cur_rel = {rel0} + rand(10) - 5"), {"set_string_var": desc, "target_var": g("pf_cur_kdesc")}, m("_n = rand(%d)" % (len(names) - 1)), m("_t = rand(%d)" % (len(titles) - 1))]
    eff += [{"if": m(f"_n == {i}"), "then": [{"set_string_var": nm, "target_var": g("pf_cur_name")}]} for i, nm in enumerate(names)]
    eff += [{"if": m(f"_t == {i}"), "then": [{"set_string_var": tt, "target_var": g("pf_nb_title")}]} for i, tt in enumerate(titles)]
    KIND_SET.append({"if": m(f"pf_cur_kind == {kd}"), "then": eff})
KIND_DESC = [{"if": m(f"pf_cur_kind == {kd}"), "then": [{"set_string_var": desc, "target_var": g("pf_cur_kdesc")}]} for kd, (key, desc, names, titles, rel0) in KINDS.items()]
SUR = [m("_s = rand(%d)" % (len(SURNAMES) - 1))] + [{"if": m(f"_s == {i}"), "then": [{"set_string_var": f"<global_val:pf_nb_title> {sn}", "target_var": g("pf_cur_lead"), "parse_tags": True}]} for i, sn in enumerate(SURNAMES)]
DIRSET = [m("_d = rand(7)")] + [{"if": m(f"_d == {i}"), "then": [{"set_string_var": dn, "target_var": g("pf_cur_dir")}]} for i, dn in enumerate(DIRS8)]
RULER_YES = "pf_nb_yes"
files["neighbors.json"] = [
    # -------- contact
    eoc("PF_NB_contact_tick", [
        m(f"pf_nb_cday = {TODAY}"),
        {"u_location_variable": g("pf_kp_av")},
        {"if": m("(distance(pf_kp_av, pf_home_loc) <= 30) * (rand(1) == 0)"), "then": [{"run_eocs": "PF_NB_found"}]},
    ], "Checked once a day around 14:00: once the place has 2+ households or has held a meeting, every 5 days or so a new settlement out there takes notice (up to 3).",
        recurrence="1 hours", **{"global": True},
        condition={"and": [m(AT_HOME), m(f"{HOUR} >= 14"), m(f"{HOUR} < 15"), m(f"value_or(pf_nb_cday, -1) != {TODAY}"), m(f"value_or(pf_st_n, 0) < {NB_MAX}"),
                           m("(value_or(pf_households_n, 0) >= 1) + (value_or(pf_meetings_total, 0) >= 1) > 0"),
                           m(f"{TODAY} - value_or(pf_nb_last_found, -999) >= 5")]}),
    eoc("PF_NB_found", [
        {"if": m("has_var(pf_nb_kseed) == 0"), "then": [m("pf_nb_kseed = rand(2)")]},
        m("pf_st_i = value_or(pf_st_n, 0)"), m(f"pf_cur_kind = (pf_nb_kseed + pf_st_i) % 3"),
    ] + KIND_SET + SUR + DIRSET + [
        m("pf_cur_pact = 0"), m("pf_cur_trib = 0"), m("pf_cur_str = 10 + rand(30)"), m("pf_cur_raid = -1"),
    ] + NB_STORE + [
        m("pf_st_n = pf_st_i + 1"), m(f"pf_nb_last_found = {TODAY}"),
        line("nb_contact"),
    ], "u = avatar.  A new settlement takes notice: a keep, the eyeglasses or the woodlanders (in turn, from a random start), with a name, a leader, a direction and a first view of you."),
    # -------- the week: envoys, deliveries, tribute
    eoc("PF_NB_week_tick", [
        m(f"pf_nb_wday = {TODAY}"),
        {"u_location_variable": g("pf_kp_av")},
        m("pf_st_i = 0"), {"run_eocs": "PF_NB_upkeep", "condition": m("pf_st_i < pf_st_n"), "iterations": NB_MAX + 1},
        {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [
            m("pf_st_rot = (value_or(pf_st_rot, -1) + 1) % pf_st_n"), m("pf_st_i = pf_st_rot"), {"run_eocs": "PF_NB_envoy"}]},
    ], "One afternoon a week (day 4 of 7, 15:00-17:00): every settlement's agreement does its weekly work, and one of them (in turn) sends an envoy, if you're home.",
        recurrence="1 hours", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_st_n, 0) > 0"), m(f"{TODAY} % 7 == 4"), m(f"{HOUR} >= 15"), m(f"{HOUR} < 17"), m(f"value_or(pf_nb_wday, -1) != {TODAY}")]}),
    # full run: the tribute broke without warning (stores ran short the week it was due)
    eoc("PF_NB_trib_warn", [
        m(f"pf_nb_twday = {TODAY}"),
        m("pf_st_i = 0"), {"run_eocs": "PF_NB_trib_warn_one", "condition": m("pf_st_i < pf_st_n"), "iterations": NB_MAX + 1},
    ], "The day before the week's tribute (day 3 of 7, by day, once): if the stores can't cover it, you're told.",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_st_n, 0) > 0"), m(f"{TODAY} % 7 == 3"), m(f"{HOUR} >= 8"), m(f"{HOUR} < 20"),
                           m(f"value_or(pf_nb_twday, -1) != {TODAY}"), {"not": {"u_has_effect": "sleep"}}]}),
    eoc("PF_NB_trib_warn_one", NB_LOAD + [
        {"run_eocs": "PF_STORES_count", "alpha_talker": "avatar"},
        {"if": m("(pf_cur_trib == 1) * (value_or(pf_stores, 0) + pf_dr_real < 5)"), "then": [m("pf_nb_tw_have = value_or(pf_stores, 0) + pf_dr_real"), line("nb_tribute_warn")]},
        m("pf_st_i += 1")]),
    eoc("PF_NB_upkeep", NB_LOAD + [
        {"if": m("pf_cur_pact == 1"), "then": [
            # v0.7: while you're away the goods wait in the pantry (gen_away.py), not on an unloaded map
            {"if": m("value_or(pf_aw_state, 0) == 1"), "then": [{"run_eocs": "PF_AW_delivery"}], "else": [
            {"if": m("pf_cur_kind == 2"), "then": [{"map_spawn_item": "pemmican", "loc": g("pf_stores_loc"), "count": 3}, {"map_spawn_item": "seed_potato_raw", "loc": g("pf_stores_loc"), "count": 5}]},
            {"if": m("pf_cur_kind == 1"), "then": [{"map_spawn_item": "aspirin", "loc": g("pf_stores_loc"), "count": 10}, {"map_spawn_item": "bandages", "loc": g("pf_stores_loc"), "count": 5}]},
            {"if": m("pf_cur_kind == 0"), "then": [{"map_spawn_item": "bolt_metal", "loc": g("pf_stores_loc"), "count": 10}]},
            {"if": m(CALM), "then": [line("nb_delivery")]}]},
            m("pf_cur_rel = min(pf_cur_rel + 2, 100)")]},
        {"if": m("pf_cur_trib == 1"), "then": [
            m("pf_dr_want = 5"), m("pf_dr_all = 1"), {"run_eocs": "PF_STORES_draw", "alpha_talker": "avatar"},
            {"if": m("value_or(pf_stores, 0) >= 5"), "then": [m("pf_stores -= 5"), {"if": m(CALM), "then": [line("nb_tribute_paid")]}],
             "else": [m("pf_cur_trib = 0"), m("pf_cur_rel -= 25"), line("nb_tribute_short")]}]},
        {"if": m("(pf_cur_rel <= -30) * (pf_cur_raid < 0) * (pf_cur_kin == 0)"), "then": [m(f"pf_cur_raid = {TODAY} + 1 + rand(2)"), line("nb_arming")]},
    ] + NB_STORE + [m("pf_st_i += 1")], "One settlement's week: what an agreement brings (the woodlanders' food and seed, the eyeglasses' medicine, the keep's bolts), tribute paid out of the stores (or the agreement breaks), and a hostile one starts arming (a raid in 1-3 nights)."),
    eoc("PF_NB_offer", NB_LOAD + KIND_DESC + [
        m("pf_nb_off = 0"),
        {"if": m("pf_cur_rel <= -30"), "then": [m("pf_nb_off = -1")],
         "else": [{"if": m("(pf_cur_rel >= 40) * (pf_cur_pact != 2)"), "then": [m("pf_nb_off = 2")],
                   "else": [{"if": m("(pf_cur_kind == 0) * (pf_cur_trib == 0) * (pf_cur_pact == 0)"), "then": [m("pf_nb_off = 3")],
                             "else": [{"if": m("pf_cur_pact == 0"), "then": [m("pf_nb_off = 1")]}]}]}]},
        # pass 6: a settlement that's family-minded (50+, already agreed, not yet kin) may offer a match instead of a courtesy visit
        {"if": m("(pf_nb_off == 0) * (pf_cur_rel >= 50) * (pf_cur_pact >= 1) * (pf_cur_kin == 0) * (value_or(pf_nb_mpend, 0) == 0) * ((rand(1) == 0) + value_or(pf_kl_nb_match, 0) > 0)"),
         "then": [m("pf_nb_off = 4")]},
        {"switch": m("pf_nb_off"), "cases": [
            {"case": -1, "effect": [line("nb_no_envoy")]},
            {"case": 0, "effect": [m("pf_cur_rel = min(pf_cur_rel + 5, 100)"), line("nb_courtesy")]},
            {"case": 1, "effect": [
                {"if": m("pf_cur_kind == 1"),
                 "then": [{"set_string_var": "An envoy from <global_val:pf_cur_name> wants everyone here registered and counted.  In return: medicine, every week.  Agree?", "target_var": g("pf_nb_q"), "parse_tags": True}],
                 "else": [{"set_string_var": "An envoy from <global_val:pf_cur_name> offers to trade: what they have for what you have, every week.  Agree?", "target_var": g("pf_nb_q"), "parse_tags": True}]},
                line("nb_envoy"), {"run_eocs": "PF_NB_decide"},
                {"if": m(RULER_YES), "then": [m("pf_cur_pact = 1"), m("pf_cur_rel += 15"), m("pf_st_pacts = value_or(pf_st_pacts, 0) + 1"), line("nb_trade_yes")],
                 "else": [m("pf_cur_rel -= 5"), line("nb_trade_no")]}]},
            {"case": 2, "effect": [
                {"set_string_var": "<global_val:pf_cur_lead> of <global_val:pf_cur_name> proposes a pact: if either place is attacked, the other comes.  Agree?", "target_var": g("pf_nb_q"), "parse_tags": True},
                line("nb_envoy"), {"run_eocs": "PF_NB_decide"},
                {"if": m(RULER_YES), "then": [m("pf_cur_pact = 2"), m("pf_cur_rel += 10"), m("pf_st_allied = 1"), {"copy_var": g("pf_cur_name"), "target_var": g("pf_st_ally_name")},
                                             m("pf_st_pacts = value_or(pf_st_pacts, 0) + 1"), line("nb_pact_yes")],
                 "else": [m("pf_cur_rel -= 10"), line("nb_pact_no")]}]},
            {"case": 3, "effect": [
                m("pf_nb_have = value_or(pf_stores, 0)"),
                {"set_string_var": "<global_val:pf_cur_lead> of <global_val:pf_cur_name> sends word: the land is theirs, and so is a share of what grows on it.  Five stores a week.  (The stores hold <global_val:pf_nb_have>.)  Pay?", "target_var": g("pf_nb_q"), "parse_tags": True},
                line("nb_envoy"), m("pf_nb_tribute = 1"), {"run_eocs": "PF_NB_decide"}, m("pf_nb_tribute = 0"),
                {"if": m(RULER_YES), "then": [m("pf_cur_trib = 1"), m("pf_cur_rel += 10"), line("nb_tribute_yes")],
                 "else": [m("pf_cur_rel -= 30"), line("nb_tribute_no")]}]},
            {"case": 4, "effect": [line("nb_envoy"), {"run_eocs": "PF_NB_match_offer"}]}]},
    ] + NB_STORE, "u = avatar.  What one settlement's envoy says at the gate (pass 6: the envoy walks in first, PF_NB_envoy), by how things stand: a family-minded one may offer a match (pass 6); hostile ones send nobody (they're arming); a friendly one (40+) offers to stand together; a keep with no agreement demands tribute; the eyeglasses offer registration for medicine, the woodlanders (and a keep that wants trade) offer trade; anyone already agreed just pays a courtesy visit (+5)."),
    eoc("PF_NB_decide", [
        m("pf_nb_yes = 0"),
        {"if": m(COUNCIL_ON), "then": [{"run_eocs": "PF_NB_council_decides"}], "else": [
        {"if": m("value_or(pf_chief_set, 0) == 1"), "then": [
            {"copy_var": g("pf_chief_uid"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
            {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_NB_chief_decides", "alpha_talker": g("pf_find_who")}],
             "else": [{"if": {"u_query": g("pf_nb_q"), "default": False}, "then": [m("pf_nb_yes = 1")]}]}],
         "else": [{"if": {"u_query": g("pf_nb_q"), "default": False}, "then": [m("pf_nb_yes = 1")]}]}]},
    ], "u = avatar.  Who answers an envoy: the council if there is one (pass 6), else the chief (or lord) if someone else holds the chair and is here, else you (a popup)."),
    eoc("PF_NB_chief_decides", [name_into("pf_kd_judge"), {"run_eocs": "PF_NB_vote_calc"},
        {"if": m("pf_nb_yes"), "then": [line("nb_chief_yes")], "else": [line("nb_chief_no")]}]),
    eoc("PF_NB_vote_calc", [
        {"if": m("value_or(pf_nb_tribute, 0) == 1"),
         "then": [m("pf_nb_yes = (value_or(pf_stores, 0) >= 15) * (u_has_trait('PF_Q_PROUD') == 0) * (u_has_trait('PF_Q_LOYAL') + u_has_trait('PF_Q_MOTHER_HEN') + rand(1) > 0)")],
         "else": [m("pf_nb_yes = (pf_cur_rel + u_has_trait('PF_T_SOCIABLE') * 20 + u_has_trait('PF_Q_MOTHER_HEN') * 10 - u_has_trait('PF_Q_GRUDGE') * 20 + rand(20) - 10) >= 0")]},
    ], "u = the chief (or a councillor).  Tribute: they pay if the stores can bear it, unless they're proud (loyal and mother-hen chiefs pay; others half the time).  Anything else: their temperament plus how things stand with that settlement."),
    # -------- raids
    eoc("PF_NB_raid_tick", [
        m(f"pf_nb_rnight = {TODAY}"),
        m("pf_st_i = 0"), m("pf_nb_raided = 0"),
        {"run_eocs": "PF_NB_raid_check", "condition": m("(pf_st_i < pf_st_n) * (pf_nb_raided == 0)"), "iterations": NB_MAX + 1},
    ], "Every 30 minutes between 01:00 and 04:00, once a night: a settlement whose raid is due hits the place (one raid a night).",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_st_n, 0) > 0"), m(f"{HOUR} >= 1"), m(f"{HOUR} < 4"), m(f"value_or(pf_nb_rnight, -1) != {TODAY}")]}),
    eoc("PF_NB_raid_check", NB_LOAD + [
        {"if": m(f"(pf_cur_raid >= 0) * (pf_cur_raid <= {TODAY})"), "then": [m("pf_nb_raided = 1"), {"run_eocs": "PF_NB_raid"}]},
        m("pf_st_i += 1"),
    ]),
    # full run day 139: a raid at home was one line while you slept on through it; now it's loud enough to wake you
    # (vanilla wakes a sleeper on a sound louder than 2d15 after hearing)
    eoc("PF_NB_raid", [
        m("pf_cur_raid = -1"), m("pf_raids_total = value_or(pf_raids_total, 0) + 1"),
        {"u_location_variable": g("pf_kp_av")}, m("pf_nb_here = distance(pf_kp_av, pf_home_loc) <= 40"),
        {"run_eocs": "PF_KEEP_count"},
        # v0.7: while you're away the bubble is empty; the household roll (gen_away.py) says who's there
        {"if": m("value_or(pf_aw_state, 0) == 1"), "then": [m("pf_kp_n = value_or(pf_hh_adults, 0)")]},
        m("pf_nb_def = 2 * (value_or(pf_wall_state, 0) == 2) + 2 * value_or(pf_wt_on, 0) + floor(value_or(pf_kp_n, 0) / 3) + value_or(pf_st_allied, 0)"),
        m("pf_nb_att = floor(pf_cur_str / 8) + rand(2) + value_or(pf_kl_nb_force, 0) * 99"),
        {"if": m("pf_nb_def >= pf_nb_att"),
         "then": [m("pf_cur_rel -= 5"), m("pf_raids_repelled = value_or(pf_raids_repelled, 0) + 1"),
                  {"if": m("value_or(pf_aw_state, 0) == 1"), "then": [m("pf_aw_raid_held = 1"), {"run_eocs": "PF_AW_raid_news"}],
                   "else": [{"if": m("pf_nb_here"), "then": [RAID_NOISE("gunfire and shouting at the wall"), line("nb_raid_repelled")],
                             "else": [line("nb_raid_repelled_away")]}]}],
         "else": [m("pf_nb_took = min(value_or(pf_stores, 0), 10)"), m("pf_stores = value_or(pf_stores, 0) - pf_nb_took"), m("pf_cur_rel -= 5"),
                  # full run day 139: "the stores are bare" with 40 oatmeal, potatoes, soup and 62 aspirin on the shelf.  pf_stores
                  # counts only farm surplus; with none, the raiders take a third of the real food and medicine (up to 10).
                  {"if": {"and": [m("pf_nb_took <= 0"), m("pf_nb_here"), m("has_var(pf_stores_loc)")]}, "then": [
                      m("pf_nb_real = 0"),
                      {"u_map_run_item_eocs": "all", "loc": g("pf_stores_loc"), "min_radius": 0, "max_radius": 2,
                       "search_data": [{"category": ["food", "drugs"]}],
                       "true_eocs": [{"id": "PF_NB_raid_count", "effect": [m("pf_nb_real += 1")]}]},
                      m("pf_nb_rtake = min(10, floor((pf_nb_real + 2) / 3))"),
                      {"u_map_run_item_eocs": "all", "loc": g("pf_stores_loc"), "min_radius": 0, "max_radius": 2,
                       "search_data": [{"category": ["food", "drugs"]}],
                       "true_eocs": [{"id": "PF_NB_raid_take", "effect": [
                           {"if": m("pf_nb_took < pf_nb_rtake"), "then": [m("pf_nb_took += 1"), "npc_die"]}]}]}]},
                  {"set_string_var": "", "target_var": g("pf_nb_hurt")},
                  {"if": m("value_or(pf_aw_state, 0) == 1"), "then": [m("pf_aw_raid_held = 0"), {"run_eocs": "PF_AW_raid_news"}], "else": [
                  {"if": m("pf_nb_here"), "then": [
                      RAID_NOISE("shouting, running feet and something breaking"),
                      m("pf_nb_h = 0"),
                      {"u_run_npc_eocs": [{"id": "PF_NB_raid_wound", "condition": {"and": [ADULT_RES, m("pf_nb_h == 0"), m("rand(2) == 0")]}, "effect": [
                          m("pf_nb_h = 1"), m("u_hp('torso') = max(u_hp('torso') - 15, 1)"), {"u_add_effect": "bleed", "duration": "5 minutes", "target_part": "torso"},
                          name_into("pf_nb_hurt")]}], "local": True, "npc_range": 60},
                      # Kinfold day 128: the stores were empty; "they take 0 of the stores" would be the line
                      {"if": m("pf_nb_took <= 0"), "then": [{"if": m("pf_nb_h == 1"), "then": [line("nb_raid_empty_hurt")], "else": [line("nb_raid_empty")]}],
                       "else": [{"if": m("pf_nb_h == 1"), "then": [line("nb_raid_hit_hurt")], "else": [line("nb_raid_hit")]}]},
                      # full run: a raid was one line in the night; in daylight, the place shows it
                      m(f"pf_nb_af_day = {TODAY}"), m("pf_nb_af_took = pf_nb_took"),
                      {"copy_var": g("pf_cur_name"), "target_var": g("pf_nb_af_name")}, {"copy_var": g("pf_cur_dir"), "target_var": g("pf_nb_af_dir")}],
                   "else": [line("nb_raid_hit_away")]}]}]},
    ] + NB_STORE, "u = avatar, current settlement.  A raid, decided by strength against defense: the wall (+2), the watch being up (+2), a third of the grown-ups, an ally (+1), against an eighth of their people plus luck.  Held: they're driven off.  Not held: they take up to 10 stores and, if you're home, someone is hurt (a resident who was out there, bleeding).  Either way they think less of you."),
]
files["neighbors.json"].append(eoc("PF_NB_raid_after", [
    m("pf_nb_af_day = -1"),
    {"if": m("pf_nb_af_took <= 0"), "then": [line("nb_raid_after_empty")],
     "else": [{"if": m("value_or(pf_wall_state, 0) == 2"), "then": [line("nb_raid_after_wall")], "else": [line("nb_raid_after")]}]},
], "The morning after a raid got through while you were home: where they came in, and what's gone.",
    recurrence="10 minutes", **{"global": True},
    condition={"and": [m(AT_HOME), m(f"value_or(pf_nb_af_day, -1) == {TODAY}"), m(f"{HOUR} >= 6"), m(f"{HOUR} < 20"),
                       {"not": {"u_has_effect": "sleep"}}]}))
LINES.update({
    "nb_contact": ("A rider comes up the road and stops at a distance, looking the place over: from <global_val:pf_cur_name>, out to the <global_val:pf_cur_dir>, <global_val:pf_cur_kdesc>.  <global_val:pf_cur_lead> sends greetings.  Or a warning.  Hard to tell.", "info"),
    "nb_envoy": ("An envoy from <global_val:pf_cur_name> comes to the gate, with <global_val:pf_cur_lead>'s words.", "info"),
    "nb_courtesy": ("An envoy from <global_val:pf_cur_name> drops by: news, gossip, a bottle passed round.  Things are good with them.", "good"),
    "nb_no_envoy": ("Nobody comes from <global_val:pf_cur_name> this week.  Smoke on the <global_val:pf_cur_dir> horizon, at their end.", "bad"),
    "nb_trade_yes": ("It's agreed: from now on, every week, something comes from <global_val:pf_cur_name>.", "good"),
    "nb_trade_no": ("The envoy from <global_val:pf_cur_name> shrugs and goes.", "info"),
    "nb_pact_yes": ("A pact with <global_val:pf_cur_name>: if either place is attacked, the other comes.  Hands are shaken on it.", "good"),
    "nb_pact_no": ("The envoy from <global_val:pf_cur_name> takes the refusal politely, and doesn't come back soon.", "info"),
    "nb_tribute_yes": ("So it's tribute to <global_val:pf_cur_name>, five stores a week.  Nobody likes it.  Nobody gets hurt, either.", "info"),
    "nb_tribute_no": ("The answer goes back to <global_val:pf_cur_lead>: no.  The envoy looks at the wall for a long time before leaving.", "bad"),
    "nb_tribute_paid": ("The tribute goes out to <global_val:pf_cur_name>: five stores.", "info"),
    "nb_tribute_warn": ("Tomorrow the tribute to <global_val:pf_cur_name> is due: five stores, and there are only <global_val:pf_nb_tw_have>.  If it isn't there, the agreement's off, and they won't take it kindly.", "bad"),
    "nb_tribute_short": ("There's not enough to pay <global_val:pf_cur_name> this week.  Their envoy leaves without a word.", "bad"),
    "nb_delivery": ("Carts come from <global_val:pf_cur_name>, as agreed.  The goods are at home.", "good"),
    "nb_arming": ("Word comes from the road: <global_val:pf_cur_name> is arming.  Not for the dead.", "bad"),
    "nb_chief_yes": ("<global_val:pf_kd_judge> is chief, so it's their answer: yes.", "info"),
    "nb_chief_no": ("<global_val:pf_kd_judge> is chief, so it's their answer: no.", "info"),
    "nb_raid_repelled": ("Shots in the dark from the <global_val:pf_cur_dir>: raiders from <global_val:pf_cur_name>.  The wall holds, the watch fires back, and by the time anyone gets there, they're gone.", "good"),
    "nb_raid_repelled_away": ("Word reaches you: raiders from <global_val:pf_cur_name> tried the place in the night, and were driven off.", "good"),
    "nb_raid_hit": ("Raiders from <global_val:pf_cur_name>, out of the <global_val:pf_cur_dir>, in the dark.  By the time anyone gets there, they're gone, and so are <global_val:pf_nb_took> of the stores.", "bad"),
    "nb_raid_hit_hurt": ("Raiders from <global_val:pf_cur_name>, out of the <global_val:pf_cur_dir>.  They take <global_val:pf_nb_took> of the stores, and <global_val:pf_nb_hurt> is hurt trying to stop them.", "bad"),
    "nb_raid_empty": ("Raiders from <global_val:pf_cur_name>, out of the <global_val:pf_cur_dir>, in the dark.  They find the stores bare, and take it out on everything else before they go.", "bad"),
    "nb_raid_empty_hurt": ("Raiders from <global_val:pf_cur_name>, out of the <global_val:pf_cur_dir>.  The stores are bare, so they take it out on whoever's in the way: <global_val:pf_nb_hurt> is hurt trying to stop them.", "bad"),
    "nb_raid_after_empty": ("In daylight you can see what they did: the empty store shelves kicked over, a water barrel split, mud everywhere on the <global_val:pf_nb_af_dir> side.  There was nothing to take, so they broke what they could.", "bad"),
    "nb_raid_after": ("In daylight you can see how they came: boot prints in the mud on the <global_val:pf_nb_af_dir> side, the fence cut and bent back, a dropped glove.  <global_val:pf_nb_af_took> stores gone.  Nobody says much at breakfast.", "bad"),
    "nb_raid_after_wall": ("In daylight you can see how they came: a ladder still leaning on the <global_val:pf_nb_af_dir> wall, rope marks on the top, mud tracked to the stores.  <global_val:pf_nb_af_took> of them gone.  People keep looking at the wall.", "bad"),
    "nb_raid_hit_away": ("Word reaches you: raiders from <global_val:pf_cur_name> hit the place in the night and took <global_val:pf_nb_took> of the stores.", "bad"),
    "nb_list": ("<global_val:pf_cur_name>, out to the <global_val:pf_cur_dir> (<global_val:pf_cur_lead>): <global_val:pf_cur_relw>; <global_val:pf_cur_pactw>.", "info"),
    "nb_none": ("Nobody out there has taken notice of the place yet.", "info"),
    "siege_allies": ("Riders from <global_val:pf_st_ally_name> hit the horde's flank, as agreed.  Fewer of them reach the wall.", "good"),
})
files["lines.json"] = [eoc("PF_SAY_keep", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Keep lines, picked by the context var 'line'.")]
files["neighbors.json"].append(eoc("PF_NB_menu", [
    {"if": m("value_or(pf_st_n, 0) == 0"), "then": [line("nb_none")]},
    m("pf_st_i = 0"),
    {"run_eocs": {"id": "PF_NB_list_one", "effect": NB_LOAD + REL_WORD + PACT_WORD + [line("nb_list"), m("pf_st_i += 1")]},
     "condition": m("pf_st_i < value_or(pf_st_n, 0)"), "iterations": NB_MAX + 1},
], "u = avatar.  Home menu: The neighbors.", condition=m(AT_HOME)))
files["lab_keep.json"] += [
    eoc("PF_KL_nb_contact", [{"if": m(f"value_or(pf_st_n, 0) < {NB_MAX}"), "then": [{"run_eocs": "PF_NB_found"}], "else": [say("[keep lab] Three settlements already know of you.")]}]),
    eoc("PF_KL_nb_envoy", [{"if": m("value_or(pf_st_n, 0) > 0"), "then": [
        {"u_location_variable": g("pf_kp_av")},
        m("pf_st_rot = (value_or(pf_st_rot, -1) + 1) % pf_st_n"), m("pf_st_i = pf_st_rot"), {"run_eocs": "PF_NB_envoy"}],
        "else": [say("[keep lab] Nobody knows of the place yet.")]}]),
    eoc("PF_KL_nb_week", [{"if": m("value_or(pf_st_n, 0) > 0"), "then": [m("pf_st_i = 0"), {"run_eocs": "PF_NB_upkeep", "condition": m("pf_st_i < pf_st_n"), "iterations": NB_MAX + 1}],
                           "else": [say("[keep lab] Nobody knows of the place yet.")]}], "Keep lab: a week's agreements, tribute and arming, now."),
    eoc("PF_KL_nb_raid", [{"if": m("value_or(pf_st_n, 0) > 0"), "then": [
        m("pf_st_i = 0")] + NB_LOAD + [{"run_eocs": "PF_NB_raid"}],
        "else": [say("[keep lab] Nobody knows of the place yet.")]}], "Keep lab: the first settlement raids the place now."),
    eoc("PF_KL_nb_raid_win", [{"if": m("value_or(pf_st_n, 0) > 0"), "then": [
        m("pf_st_i = 0"), m("pf_stores = max(value_or(pf_stores, 0), 12)"), m("pf_kl_nb_force = 1")] + NB_LOAD + [{"run_eocs": "PF_NB_raid"}, m("pf_kl_nb_force = 0")],
        "else": [say("[keep lab] Nobody knows of the place yet.")]}], "Keep lab: the first settlement raids the place now, and gets through (the stores are topped up to 12 first)."),
    eoc("PF_KL_nb_sour", [{"if": m("value_or(pf_st_n, 0) > 0"), "then": [m("pf_st_i = 0")] + NB_LOAD + [m("pf_cur_rel = -40")] + NB_STORE + [
        say("[keep lab] <global_val:pf_cur_name> is hostile now (the next week, they arm).")], "else": [say("[keep lab] Nobody knows of the place yet.")]}]),
    eoc("PF_KL_nb_warm", [{"if": m("value_or(pf_st_n, 0) > 0"), "then": [m("pf_st_i = 0")] + NB_LOAD + [m("pf_cur_rel = 50")] + NB_STORE + [
        say("[keep lab] <global_val:pf_cur_name> is friendly now (their next envoy offers a pact).")], "else": [say("[keep lab] Nobody knows of the place yet.")]}]),
]


# ============================================================ PASS 6: THE COUNCIL, ENVOYS WHO WALK IN, MATCHES
# ---------------- the council (law 7): three seats chosen by the meeting; the speaker (most hands) is also the chief
def council_round(member_eoc, you_effects):
    """Effects (u = avatar): every councillor who's here has their say: an NPC runs member_eoc (as alpha), you run
    you_effects if you hold a seat and are at home.  pf_cnv_here counts who was there."""
    eff = [{"u_location_variable": g("pf_kp_av")}, m("pf_cnv_here = 0")]
    for k in (1, 2, 3):
        eff.append({"if": m(f"value_or(pf_cn_n, 0) >= {k}"), "then": [
            {"if": {"compare_string": [g(f"pf_cn_uid_{k}"), "AVATAR"]},
             "then": [{"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [m("pf_cnv_here += 1")] + you_effects}],
             "else": [{"copy_var": g(f"pf_cn_uid_{k}"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
                      {"if": m("pf_find_ok == 1"), "then": [m("pf_cnv_here += 1"), {"run_eocs": member_eoc, "alpha_talker": g("pf_find_who")}]}]}]})
    return eff
def seat_pick(k):
    return eoc(f"PF_KEEP_cn_seat_{k}", [
        m("pf_kw_best = 0"), m("pf_kw_sel = 0"),
        {"u_run_npc_eocs": [{"id": f"PF_KEEP_cn_count_{k}", "condition": {"and": [ADULT_RES, m("value_or(u_pf_cn_term, -1) != pf_cn_term")]}, "effect": [
            {"set_string_var": "pf_kv_<u_val:pf_uid>", "target_var": ctx("kv"), "parse_tags": True},
            {"if": m("value_or(v_kv, 0) > pf_kw_best"), "then": [m("pf_kw_best = v_kv"), m("pf_kw_sel = 1"),
                                                                  {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kw_uid")}, name_into("pf_kw_name")]}]}],
         "local": True, "npc_range": 60},
        {"if": m("(pf_ke_you == 1) * (pf_cn_youin == 0) * (pf_kv_AVATAR > pf_kw_best)"), "then": [m("pf_kw_best = pf_kv_AVATAR"), m("pf_kw_sel = 2")]},
        {"if": m("pf_kw_sel == 2"), "then": [m("pf_cn_n += 1"), m("pf_cn_youin = 1"), m(f"pf_cn_v_{k} = pf_kw_best"),
                                             {"set_string_var": "AVATAR", "target_var": g(f"pf_cn_uid_{k}")}, {"set_string_var": "you", "target_var": g(f"pf_cn_name_{k}")}]},
        {"if": m("pf_kw_sel == 1"), "then": [m("pf_cn_n += 1"), m(f"pf_cn_v_{k} = pf_kw_best"),
                                             {"copy_var": g("pf_kw_uid"), "target_var": g(f"pf_cn_uid_{k}")}, {"copy_var": g("pf_kw_name"), "target_var": g(f"pf_cn_name_{k}")},
                                             {"copy_var": g("pf_kw_uid"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
                                             {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_KEEP_cn_mark", "alpha_talker": g("pf_find_who")}]}]},
    ], f"u = avatar.  Seat {k}: whoever has the most hands among those not yet seated (at least one); you, if you stood and beat them outright.",
        condition=m(f"pf_cn_n == {k - 1}"))
def vote_moments(winner, loser, judge):
    return [{"run_eocs": "PF_MK_ruled_for", "alpha_talker": judge, "beta_talker": g(f"pf_kd_{winner}")},
            {"run_eocs": "PF_MK_ruled_against", "alpha_talker": judge, "beta_talker": g(f"pf_kd_{loser}")}]
SPEAKER_SET = [
    m("pf_cn_same = 0"),
    {"if": {"and": [m("value_or(pf_chief_set, 0) == 2"), {"compare_string": [g("pf_cn_uid_1"), "AVATAR"]}]}, "then": [m("pf_cn_same = 1")]},
    {"if": {"and": [m("value_or(pf_chief_set, 0) == 1"), {"compare_string": [g("pf_cn_uid_1"), g("pf_chief_uid")]}]}, "then": [m("pf_cn_same = 1")]},
    {"if": {"compare_string": [g("pf_cn_uid_1"), "AVATAR"]},
     "then": [m("pf_chief_set = 2"), {"set_string_var": "AVATAR", "target_var": g("pf_chief_uid")}, {"set_string_var": "you", "target_var": g("pf_chief_name")}],
     "else": [m("pf_chief_set = 1"), {"copy_var": g("pf_cn_uid_1"), "target_var": g("pf_chief_uid")}, {"copy_var": g("pf_cn_name_1"), "target_var": g("pf_chief_name")}]},
    {"if": m("pf_cn_same == 0"), "then": [m("pf_chief_since = time('now')")]},
    m("pf_chief_away = 0")]
files["council.json"] = [
    eoc("PF_KEEP_council_election", [
        m("pf_ke_you = 0"), m("pf_ke_total = 0"),
        {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [
            {"if": {"u_query": "The meeting is choosing a council of three to run the place.  Will you stand for a seat?", "default": False}, "then": [m("pf_ke_you = 1")]}]},
        m("pf_kv_AVATAR = 0"),
        {"u_run_npc_eocs": [{"id": "PF_KEEP_cn_tally_reset", "condition": ADULT_RES, "effect": [
            {"set_string_var": "pf_kv_<u_val:pf_uid>", "target_var": ctx("kv"), "parse_tags": True}, m("v_kv = 0")]}], "local": True, "npc_range": 60},
        {"u_run_npc_eocs": ["PF_KEEP_cn_voter"], "local": True, "npc_range": 60},
        m("pf_cn_term = value_or(pf_cn_term, 0) + 1"), m("pf_cn_n = 0"), m("pf_cn_youin = 0"),
        {"run_eocs": "PF_KEEP_cn_seat_1"}, {"run_eocs": "PF_KEEP_cn_seat_2"}, {"run_eocs": "PF_KEEP_cn_seat_3"},
        {"if": m("pf_cn_n < 2"), "then": [m("pf_cn_n = 0"), line("council_none")], "else": SPEAKER_SET + [
            m("pf_cn_since = time('now')"), m("pf_elections_total = value_or(pf_elections_total, 0) + 1"),
            m("pf_councils_total = value_or(pf_councils_total, 0) + 1"),
            {"run_eocs": "PF_KEEP_cn_list"}, line("council_chosen")]},
    ], "u = avatar.  Under the council law: you're asked whether you'll stand, everyone puts a hand up for each of the three they'd most follow (one hand each made a small place pile every vote on one person), and the three with the most hands take the seats (at least one hand each; two seats or no council).  The one with the most speaks for it, and holds the chair as chief: they fine shirkers and are the one a confidence vote turns on."),
    eoc("PF_KEEP_cn_voter", [
        {"u_set_talker": g("pf_kv_voter")}, {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kv_vuid")},
        m("pf_c1 = -999"), m("pf_c2 = -999"), m("pf_c3 = -999")] + [{"set_string_var": "none", "target_var": g(f"pf_c{k}u")} for k in (1, 2, 3)] + [
        {"if": m("pf_ke_you == 1"), "then": [
            {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
            {"if": m("pf_read_t + pf_read_w >= 10"), "then": [m("pf_c1 = pf_read_t + pf_read_w / 2 - pf_read_x"), {"set_string_var": "AVATAR", "target_var": g("pf_c1u")}]}]},
        {"u_run_npc_eocs": [{"id": "PF_KEEP_cn_cand", "condition": {"and": [ADULT_RES, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kv_vuid")]}}]}, "effect": [
            {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_m_other")},
            {"run_eocs": "PF_VIEW_read", "alpha_talker": g("pf_kv_voter")},
            m("_s = pf_read_t + pf_read_w / 2 - pf_read_x"),
            {"if": m("pf_read_t + pf_read_w >= 10"), "then": [
                {"if": m("_s > pf_c1"), "then": [
                    m("pf_c3 = pf_c2"), {"copy_var": g("pf_c2u"), "target_var": g("pf_c3u")}, m("pf_c2 = pf_c1"), {"copy_var": g("pf_c1u"), "target_var": g("pf_c2u")},
                    m("pf_c1 = _s"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_c1u")}, {"u_set_talker": g("pf_c1t")}],
                 "else": [{"if": m("_s > pf_c2"), "then": [
                     m("pf_c3 = pf_c2"), {"copy_var": g("pf_c2u"), "target_var": g("pf_c3u")}, m("pf_c2 = _s"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_c2u")}],
                     "else": [{"if": m("_s > pf_c3"), "then": [m("pf_c3 = _s"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_c3u")}]}]}]}]}]}],
         "local": True, "npc_range": 60}] + [
        {"if": {"not": {"compare_string": [g(f"pf_c{k}u"), "none"]}}, "then": [
            {"if": {"compare_string": [g(f"pf_c{k}u"), "AVATAR"]}, "then": [m("pf_kv_AVATAR += 1")],
             "else": [{"set_string_var": f"pf_kv_<global_val:pf_c{k}u>", "target_var": ctx("kv"), "parse_tags": True}, m("v_kv = value_or(v_kv, 0) + 1")]}]}
        for k in (1, 2, 3)] + [
        {"if": {"compare_string": [g("pf_c1u"), "AVATAR"]}, "then": [m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_voted_for", "beta_talker": "avatar"}],
         "else": [{"if": {"not": {"compare_string": [g("pf_c1u"), "none"]}}, "then": [m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_voted_for", "beta_talker": g("pf_c1t")}]}]},
        m("pf_ke_total += 1"),
    ], "u = a grown-up who lives here: for the council they put a hand up for each of the three they'd most follow (among those they know: warmth + trust 10+), and the first of them gets a voted_for moment.", condition=ADULT_RES),
    seat_pick(1), seat_pick(2), seat_pick(3),
    eoc("PF_KEEP_cn_mark", [m("u_pf_cn_term = pf_cn_term")], "u = someone just given a seat: marked with this term's number."),
    eoc("PF_KEEP_cn_list", [
        {"if": m("pf_cn_n >= 3"), "then": [{"set_string_var": "<global_val:pf_cn_name_1>, <global_val:pf_cn_name_2> and <global_val:pf_cn_name_3>", "target_var": g("pf_cn_list"), "parse_tags": True}],
         "else": [{"set_string_var": "<global_val:pf_cn_name_1> and <global_val:pf_cn_name_2>", "target_var": g("pf_cn_list"), "parse_tags": True}]},
        {"if": {"compare_string": [g("pf_cn_uid_1"), "AVATAR"]}, "then": [{"set_string_var": "you speak for it", "target_var": g("pf_cn_spk")}],
         "else": [{"set_string_var": "<global_val:pf_cn_name_1> speaks for it", "target_var": g("pf_cn_spk"), "parse_tags": True}]},
    ], "u = avatar.  The council's names as a list, and who speaks for it."),
    eoc("PF_KEEP_cn_noop", [], "u = a councillor who is here (presence count)."),
    eoc("PF_KEEP_cn_present", council_round("PF_KEEP_cn_noop", []), "u = avatar.  How many of the council are here (pf_cnv_here)."),
    # quarrels: each councillor sides by their own view (and owns that ruling); the most votes decides, else they shake on it
    eoc("PF_KEEP_council_judge", [m("pf_cq_a = 0"), m("pf_cq_b = 0"), m("pf_cq_s = 0"),
        {"set_string_var": "The council hears <global_val:pf_kd_aname> and <global_val:pf_kd_bname> out: <global_val:pf_kd_topic>.  Your say: do you side with <global_val:pf_kd_aname>?", "target_var": g("pf_cq_q1"), "parse_tags": True},
        {"set_string_var": "With <global_val:pf_kd_bname>, then?  (No: they should both shake on it.)", "target_var": g("pf_cq_q2"), "parse_tags": True}] +
        council_round("PF_KEEP_cn_judge_one", [
            {"if": {"u_query": g("pf_cq_q1"), "default": False}, "then": [m("pf_cq_a += 1")] + vote_moments("a", "b", "avatar"),
             "else": [{"if": {"u_query": g("pf_cq_q2"), "default": False}, "then": [m("pf_cq_b += 1")] + vote_moments("b", "a", "avatar"),
                       "else": [m("pf_cq_s += 1")]}]}]) + [
        {"if": m("(pf_cq_a > pf_cq_b) * (pf_cq_a > pf_cq_s)"),
         "then": [{"copy_var": g("pf_kd_aname"), "target_var": g("pf_kd_wname")}, {"copy_var": g("pf_kd_bname"), "target_var": g("pf_kd_lname")},
                  m("pf_m_str_in = 20"), {"run_eocs": "PF_MK_made_peace", "alpha_talker": g("pf_kd_a"), "beta_talker": g("pf_kd_b")}, line("council_rules")],
         "else": [{"if": m("(pf_cq_b > pf_cq_a) * (pf_cq_b > pf_cq_s)"),
                   "then": [{"copy_var": g("pf_kd_bname"), "target_var": g("pf_kd_wname")}, {"copy_var": g("pf_kd_aname"), "target_var": g("pf_kd_lname")},
                            m("pf_m_str_in = 20"), {"run_eocs": "PF_MK_made_peace", "alpha_talker": g("pf_kd_a"), "beta_talker": g("pf_kd_b")}, line("council_rules")],
                   "else": SPLIT() + [line("council_split")]}]},
        m("pf_council_rulings_total = value_or(pf_council_rulings_total, 0) + 1"),
    ], "u = avatar.  A quarrel before the council: every councillor here sides with whoever they think more of (or says shake on it, if it's close), and you have your say if you hold a seat.  Each one's ruling is theirs: the winner trusts them more, the loser resents them.  The most votes decides; a tie means they shake on it."),
    eoc("PF_KEEP_cn_judge_one", [
        {"copy_var": g("pf_kd_auid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"}, m("_sa = pf_read_t + pf_read_w / 2 - pf_read_x"),
        {"copy_var": g("pf_kd_buid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"}, m("_sb = pf_read_t + pf_read_w / 2 - pf_read_x"),
        {"if": m("abs(_sa - _sb) < 5"), "then": [m("pf_cq_s += 1")],
         "else": [{"if": m("_sa > _sb"), "then": [m("pf_cq_a += 1")] + vote_moments("a", "b", "u"), "else": [m("pf_cq_b += 1")] + vote_moments("b", "a", "u")}]},
    ], "u = a councillor (not one of the two quarrelling): their own ruling.",
        condition={"and": [{"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kd_auid")]}}, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kd_buid")]}}]}),
    # the door: the council talks it over (a tie lets them in); with none of them here, it's yours
    eoc("PF_KEEP_council_door", [m("pf_cnv_y = 0"), m("pf_cnv_no = 0"),
        {"set_string_var": "<global_val:pf_tj_name> and their family are at the door, asking to live here.  It's for the council.  Your say: do you take them in?", "target_var": g("pf_cn_q"), "parse_tags": True}] +
        council_round("PF_KEEP_cn_door_one", [{"if": {"u_query": g("pf_cn_q"), "default": True}, "then": [m("pf_cnv_y += 1")], "else": [m("pf_cnv_no += 1")]}]) + [
        {"if": m("pf_cnv_here == 0"),
         "then": [{"if": {"u_query": g("pf_tj_q"), "default": True}, "then": [m("pf_cnv_yes_all = 1")], "else": [m("pf_cnv_yes_all = 0")]}],
         "else": [m("pf_cnv_yes_all = pf_cnv_y >= pf_cnv_no"), {"if": m("pf_cnv_yes_all"), "then": [line("council_door_yes")], "else": [line("council_door_no")]}]},
        {"if": m("value_or(pf_kl_dry, 0) == 0"), "then": [{"if": m("pf_cnv_yes_all"), "then": [{"run_eocs": "PF_TOWN_join_yes"}], "else": [{"run_eocs": "PF_TOWN_join_no"}]}]},
    ], "u = avatar.  Under the council, a family at the door is the council's call: each councillor here as a chief would decide (while the place is small they take people in; after that only the sociable and the mother hens), you too if you hold a seat.  A tie lets them in."),
    eoc("PF_KEEP_cn_door_one", [m("_y = (value_or(pf_households_n, 0) < 4) + u_has_trait('PF_T_SOCIABLE') + u_has_trait('PF_Q_MOTHER_HEN')"),
                                {"if": m("_y > 0"), "then": [m("pf_cnv_y += 1")], "else": [m("pf_cnv_no += 1")]}], "u = a councillor: yes or no at the door."),
    # envoys: the council answers (a tie is a no); with none of them here, you do
    eoc("PF_NB_council_decides", [m("pf_cnv_y = 0"), m("pf_cnv_no = 0")] +
        council_round("PF_NB_cn_vote_one", [{"if": {"u_query": g("pf_nb_q"), "default": False}, "then": [m("pf_cnv_y += 1")], "else": [m("pf_cnv_no += 1")]}]) + [
        {"if": m("pf_cnv_here == 0"), "then": [{"if": {"u_query": g("pf_nb_q"), "default": False}, "then": [m("pf_nb_yes = 1")], "else": [m("pf_nb_yes = 0")]}],
         "else": [m("pf_nb_yes = pf_cnv_y > pf_cnv_no"), {"if": m("pf_nb_yes"), "then": [line("nb_council_yes")], "else": [line("nb_council_no")]}]},
    ], "u = avatar.  Under the council, an envoy's offer is the council's to answer: each councillor here as a chief would (their temperament and how things stand), you too if you hold a seat.  A tie is a no."),
    eoc("PF_NB_cn_vote_one", [{"run_eocs": "PF_NB_vote_calc"}, {"if": m("pf_nb_yes"), "then": [m("pf_cnv_y += 1")], "else": [m("pf_cnv_no += 1")]}], "u = a councillor: yes or no to the envoy."),
    # losing a councillor (not the speaker: that's the chief's death): the meeting chooses again the next evening
    eoc("PF_KEEP_cn_on_death", [m("pf_cn_n = 0"), m("pf_mt_due = 1"), name_into("pf_cn_dead_name"),
                                {"run_eocs": "PF_SAY_keep", "alpha_talker": "avatar", "variables": {"line": "council_lost"}}],
        "A councillor died: the council is a seat short, and the meeting chooses it again the next evening.",
        condition={"and": ["has_alpha", "u_is_npc", m("has_var(u_pf_uid)"), IS_COUNCIL, {"not": IS_CHIEF}]},
        eoc_type="EVENT", required_event="character_dies"),
]

# ---------------- envoys who walk in: someone real comes up the road, says it at the door, and goes home
DIRV = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
DIRN = [m("pf_nv_dx = 0"), m("pf_nv_dy = -1")] + [
    {"if": {"compare_string": [g("pf_cur_dir"), dn]}, "then": [m(f"pf_nv_dx = {dx}"), m(f"pf_nv_dy = {dy}")]} for dn, (dx, dy) in zip(DIRS8, DIRV)]
NV_T = {0: ("PF_NV_KEEP", "NC_SOLDIER"), 1: ("PF_NV_EYES", "NC_DOCTOR"), 2: ("PF_NV_WOOD", "NC_HUNTER")}
files["visitors.json"] = [
    {"type": "npc", "id": t, "//": "An envoy from a settlement out there (Keep pass 6).  Mission 2: walk orders only.  Comes and goes; removed once out of sight (lifespan 1 day as a safety net: no corpse).",
     "name_suffix": "envoy", "class": cls, "attitude": 0, "mission": 2, "chat": "TALK_PF_NV", "faction": "no_faction"}
    for k, (t, cls) in NV_T.items()] + [
    {"type": "npc", "id": f"PF_MATCH_{k}_{gn}", "//": "Someone from a settlement out there, coming to marry one of yours (Keep pass 6).",
     "class": NV_T[k][1], "attitude": 0, "mission": 2, "chat": "TALK_PF_PERSON", "faction": "no_faction", "gender": gn}
    for k in NV_T for gn in ("male", "female")] + [
    {"type": "talk_topic", "id": "TALK_PF_NV", "dynamic_line": "<global_val:pf_nv_says>",
     "responses": [{"text": "Safe road.", "topic": "TALK_DONE"}]},
]
files["neighbors.json"] += [
    eoc("PF_NB_envoy", NB_LOAD + [
        {"if": m("pf_cur_rel <= -30"), "then": [line("nb_no_envoy")], "else": [
            {"if": m("value_or(pf_nv_state, 0) > 0"), "then": [line("nv_busy")], "else": DIRN + [
                {"copy_var": g("pf_home_loc"), "target_var": g("pf_nv_at")},
                {"location_variable_adjust": g("pf_nv_at"), "x_adjust": m("pf_nv_dx * 22"), "y_adjust": m("pf_nv_dy * 22")},
                {"copy_var": g("pf_home_loc"), "target_var": g("pf_nv_door")},
                {"location_variable_adjust": g("pf_nv_door"), "x_adjust": m("pf_nv_dx * 3"), "y_adjust": m("pf_nv_dy * 3")},
                m("pf_nv_seq = value_or(pf_nv_seq, 0) + 1"),
                {"set_string_var": "PF_NV_<global_val:pf_nv_seq>", "target_var": g("pf_nv_uid"), "parse_tags": True},
                {"copy_var": g("pf_cur_name"), "target_var": g("pf_nv_from")}, {"copy_var": g("pf_cur_lead"), "target_var": g("pf_nv_lead")},
                {"copy_var": g("pf_cur_dir"), "target_var": g("pf_nv_dir")},
                {"set_string_var": "I've come from <global_val:pf_nv_from>, with word from <global_val:pf_nv_lead>.  It's for your door, where everyone can hear it.", "target_var": g("pf_nv_says"), "parse_tags": True},
                m("pf_nv_ok = 0")] + [
                {"if": m(f"pf_cur_kind == {k}"), "then": [{"u_spawn_npc": t, "unique_id": g("pf_nv_uid"), "real_count": 1, "target_var": g("pf_nv_at"),
                                                           "min_radius": 0, "max_radius": 6, "outdoor_only": True, "lifespan": "1 d"}]}
                for k, (t, cls) in NV_T.items()] + [
                by_uid(["PF_NB_nv_init"], g("pf_nv_uid")),
                {"if": m("pf_nv_ok == 1"), "then": [m("pf_nv_state = 1"), m("pf_nv_t = time('now')"), m("pf_nv_st = pf_st_i"), line("nv_coming")],
                 "else": [{"run_eocs": "PF_NB_offer"}]}]}]},
    ], "u = avatar, pf_st_i = the settlement.  Pass 6: the envoy is a real person.  They're spawned 22 tiles out in the settlement's direction and walk to your door (one envoy on the road at a time); if nowhere out there will hold them, the word just arrives, as before.  Hostile settlements send nobody."),
    eoc("PF_NB_nv_init", [m("pf_nv_ok = 1"), m("u_pf_envoy = 1"), m("u_pf_nv_gone = 0"), name_into("pf_nv_name"), {"u_set_guard_pos": g("pf_nv_door")}],
        "u = the envoy, just spawned: marked, named, and sent to the door."),
    eoc("PF_NB_nv_tick", [
        {"u_location_variable": g("pf_nv_av")},
        # never touch the envoy while you're away: reading an off-screen position loads a whole map
        {"if": m("distance(pf_nv_av, pf_home_loc) > 40"),
         "then": [{"if": m("pf_nv_state == 1"), "then": [line("nv_missed")]}, m("pf_nv_state = 0")],
         "else": [m("pf_nv_seen = 0"), by_uid(["PF_NB_nv_step"], g("pf_nv_uid")),
                  {"if": m("pf_nv_seen == 0"), "then": [m("pf_nv_state = 0")]}]},
    ], "Every minute while an envoy is out: walking in, they're kept on their way to the door, and say their piece when they get there (or after 90 minutes, from the gate); leaving, they're removed once out of your sight.  If you go away, the visit is over (the envoy disappears on their own within the day).",
        recurrence="1 minutes", **{"global": True}, condition=m("value_or(pf_nv_state, 0) > 0")),
    eoc("PF_NB_nv_step", [
        m("pf_nv_seen = 1"), {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("pf_nv_state == 1"), "then": [
            {"if": m("(distance(u_pf_pos, pf_home_loc) <= 5) + (distance(u_pf_pos, pf_nv_av) <= 2) + (time('now') - pf_nv_t >= time('90 m')) > 0"),
             "then": [m("pf_nv_state = 2"), {"run_eocs": "PF_NB_nv_arrive", "alpha_talker": "avatar"},
                      m("u_pf_nv_gone = 1"), {"u_set_guard_pos": g("pf_nv_at")}, m("pf_nv_state = 3"), m("pf_nv_t2 = time('now')"),
                      {"set_string_var": "I've said what I came to say.  I'll carry your answer back to <global_val:pf_nv_from>.", "target_var": g("pf_nv_says"), "parse_tags": True}],
             "else": [{"u_set_guard_pos": g("pf_nv_door")}]}],
         "else": [
            {"if": {"or": [m("time('now') - pf_nv_t2 >= time('1 h')"),
                           {"and": [m("distance(u_pf_pos, pf_nv_av) >= 12"), {"not": {"line_of_sight": 60, "loc_1": g("pf_nv_av"), "loc_2": {"u_val": "pf_pos"}}}]}]},
             "then": [m("pf_nv_state = 0"), {"u_die": {"remove_corpse": True, "supress_message": True}}],
             "else": [{"u_set_guard_pos": g("pf_nv_at")}]}]},
    ], "u = the envoy (reached by unique id, only while you're near home)."),
    eoc("PF_NB_nv_arrive", [
        m("pf_st_i = pf_nv_st"), {"u_location_variable": g("pf_kp_av")},
        {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [{"run_eocs": "PF_NB_offer"}, line("nv_leaves")], "else": [line("nv_missed")]},
        m("pf_nv_visits_total = value_or(pf_nv_visits_total, 0) + 1"),
    ], "u = avatar.  The envoy is at the door: what they came to say (PF_NB_offer), and the answer goes home with them."),
    eoc("PF_NB_nv_died", [
        m("pf_nv_state = 0"), m("pf_st_i = pf_nv_st")] + NB_LOAD + [m("pf_cur_rel -= 15")] + NB_STORE + [
        {"run_eocs": "PF_SAY_keep", "alpha_talker": "avatar", "variables": {"line": "nv_dead"}}],
        "An envoy died on the way in (u = the envoy): their people think less of the place (-15).",
        condition={"and": ["has_alpha", "u_is_npc", m("value_or(u_pf_envoy, 0) == 1"), m("value_or(u_pf_nv_gone, 0) == 0")]},
        eoc_type="EVENT", required_event="character_dies"),
    # ---------------- matches: a friendly settlement offers one of theirs to marry one of yours, and they come to live here
    eoc("PF_NB_match_offer", [
        m("pf_kl_nb_match = 0"), m("pf_nb_mbest = 0"), m("pf_nb_mfound = 0"),
        {"u_run_npc_eocs": [{"id": "PF_NB_match_cand", "condition": {"and": [ADULT_RES, m("value_or(u_pf_has_sweet, 0) == 0"), m("value_or(u_pf_rom, 0) == 1"), m("u_val('age') <= 50")]}, "effect": [
            m("pf_nb_mfound = 1"),
            m("_w = 1 + u_has_trait('PF_Q_ROMANTIC') * 2 + u_has_trait('PF_T_SOCIABLE') + u_has_trait('PF_Q_LOYAL') - u_has_trait('PF_T_LONER') * 2 - u_has_trait('PF_Q_PROUD') + rand(2)"),
            {"if": m("_w > pf_nb_mbest"), "then": [m("pf_nb_mbest = _w"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_nb_mc_uid")}, name_into("pf_nb_mc_name"),
                                                  m("pf_nb_mc_or = value_or(u_pf_orient, 2)")]}]}], "local": True, "npc_range": 60},
        {"if": m("pf_nb_mfound == 0"), "then": [m("pf_cur_rel = min(pf_cur_rel + 5, 100)"), line("nb_match_nobody")],
         "else": [{"if": m("pf_nb_mbest <= 0"), "then": [line("nb_match_unwilling")], "else": [
             {"set_string_var": "<global_val:pf_cur_lead> of <global_val:pf_cur_name> offers a match: one of theirs, to marry <global_val:pf_nb_mc_name> and make a home here.  <global_val:pf_nb_mc_name> is willing.  Agree?",
              "target_var": g("pf_nb_q"), "parse_tags": True},
             {"run_eocs": "PF_NB_decide"},
             {"if": m(RULER_YES), "then": [
                 m("pf_nb_mpend = 1"), m("pf_nb_mst = pf_st_i"), m(f"pf_nb_mday = {TODAY} + 2"), m("pf_nb_mp_or = pf_nb_mc_or"),
                 {"copy_var": g("pf_nb_mc_uid"), "target_var": g("pf_nb_mp_uid")}, {"copy_var": g("pf_nb_mc_name"), "target_var": g("pf_nb_mp_name")},
                 m("pf_cur_rel += 10"), line("nb_match_yes")],
              "else": [m("pf_cur_rel -= 10"), line("nb_match_no")]}]}]},
    ], "u = avatar, pf_cur_* = the settlement.  A match: the single grown-up here (romantic, unpartnered, 50 or under) who most wants one (romantics and the sociable and loyal; loners and the proud less so).  If they're willing, the ruler answers (the council, the chief, or you).  Yes: in two days someone comes to marry them."),
    eoc("PF_NB_match_tick", [
        {"u_location_variable": g("pf_kp_av")},
        {"if": m("distance(pf_kp_av, pf_home_loc) <= 30"), "then": [{"run_eocs": "PF_NB_match_arrive"}]},
    ], "Every 30 minutes, 10:00-17:00, once the day has come and you're home: the one from the other place arrives.",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_nb_mpend, 0) == 1"), m(f"{TODAY} >= pf_nb_mday"), m(f"{HOUR} >= 10"), m(f"{HOUR} < 17")]}),
    eoc("PF_NB_match_arrive", [m("pf_nb_mpend = 0"), m("pf_st_i = pf_nb_mst")] + NB_LOAD + [
        m("pf_nb_bok = 0"),
        {"copy_var": g("pf_nb_mp_uid"), "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
        {"if": m("pf_find_ok == 1"), "then": [{"copy_var": g("pf_find_who"), "target_var": g("pf_nb_bt")}, {"run_eocs": "PF_NB_match_free", "alpha_talker": g("pf_find_who")}]},
        {"if": m("pf_nb_bok == 0"), "then": [m("pf_cur_rel -= 10"), line("nb_match_off")], "else": DIRN + [
            {"copy_var": g("pf_home_loc"), "target_var": g("pf_nb_mat")},
            {"location_variable_adjust": g("pf_nb_mat"), "x_adjust": m("pf_nv_dx * 16"), "y_adjust": m("pf_nv_dy * 16")},
            # someone they can love: orientation 0 = drawn to women, 1 = men, 2 = both
            m("_g = pf_nb_mp_or == 2 ? rand(1) : pf_nb_mp_or"),
            {"run_eocs": "PF_ALIFE_register_person"}] + [
            {"if": m(f"(pf_cur_kind == {k}) * (_g == {gi})"), "then": [
                {"u_spawn_npc": f"PF_MATCH_{k}_{gn}", "unique_id": g("pf_person_uid"), "real_count": 1, "traits": ["PF_AGENT"],
                 "target_var": g("pf_nb_mat"), "min_radius": 0, "max_radius": 4, "outdoor_only": True}]}
            for k in NV_T for gi, gn in ((1, "male"), (0, "female"))] + [
            m("pf_nb_sp_ok = 0"),
            by_uid(["PF_ALIFE_store_uid", "PF_ID_ensure", "PF_NB_spouse_init"], g("pf_person_uid")),
            {"if": m("pf_nb_sp_ok == 1"), "then": [
                {"run_eocs": "PF_NB_match_bond", "alpha_talker": g("pf_nb_bt"), "beta_talker": g("pf_nb_sp_t")},
                m("pf_cur_kin = 1"), m("pf_cur_rel = min(pf_cur_rel + 15, 100)"), m("pf_st_pacts = value_or(pf_st_pacts, 0) + 1"),
                m("pf_matches_total = value_or(pf_matches_total, 0) + 1"), line("nb_match_arrive")],
             "else": [m("pf_nb_mpend = 1")]}]},
    ] + NB_STORE, "u = avatar.  The day has come: if the one promised is still here and still free, someone from the other place walks in from their direction to marry them.  They live here from now on (a resident with a job, in their partner's house), engaged, so the wedding is at the next evening's fire.  The two places are family now: no more arming against each other, and it counts toward the place's draw."),
    eoc("PF_NB_match_free", [m("pf_nb_mp_g = u_gender()"), {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 0"), m("value_or(u_pf_resident, 0) == 1")]}, "then": [m("pf_nb_bok = 1")]}],
        "u = the one promised: still unpartnered and still living here?"),
    eoc("PF_NB_spouse_init", [
        m("pf_nb_sp_ok = 1"), {"u_set_talker": g("pf_nb_sp_t")}, name_into("pf_nb_sp_name"),
        m("u_pf_adult = 1"), m("u_pf_rom = 1"), m("u_pf_rom_rolled = 1"), m("u_pf_orient = pf_nb_mp_g"), m("u_pf_commit = 1"),
        {"run_eocs": "PF_REG_write"}, m("u_pf_from_st = pf_st_i"),
        {"run_eocs": "PF_HOME_join_one"},
    ], "u = the one who came to marry: romantic, drawn to the one they're marrying, devoted (for now), and living here."),
    eoc("PF_NB_match_bond", [
        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"npc_val": "pf_sweet"}}, {"copy_var": {"npc_val": "pf_uid"}, "target_var": {"u_val": "pf_sweet"}},
        m("u_pf_has_sweet = 1"), m("n_pf_has_sweet = 1"), m("u_pf_rel_stage = 2"), m("n_pf_rel_stage = 2"),
        m("u_pf_sweet_since = time('now')"), m("n_pf_sweet_since = time('now')"), m("u_pf_stage_since = time('now')"), m("n_pf_stage_since = time('now')"),
        m("u_pf_engaged = 1"), m("n_pf_engaged = 1"), m("u_pf_wed_t = time('now')"), m("n_pf_wed_t = time('now')"),
        m("pf_m_str_in = 80"), {"run_eocs": "PF_MK_courting"}, m("pf_m_str_in = 80"), {"run_eocs": "PF_MK_courting", "alpha_talker": "npc", "beta_talker": "u"},
        m("pf_m_str_in = 80"), {"run_eocs": "PF_MK_partnered"}, m("pf_m_str_in = 70"), {"run_eocs": "PF_MK_welcomed"},
        {"if": m("has_var(u_pf_house)"), "then": [{"copy_var": {"u_val": "pf_house"}, "target_var": {"npc_val": "pf_house"}}]},
        {"if": m("has_var(u_pf_household)"), "then": [m("n_pf_household = u_pf_household")]},
    ], "u = the one promised, npc = the one who came: sweethearts, partners and engaged at once (the wedding is at the next evening's fire), with a little courting behind them so the match holds; they share a house."),
]
LINES.update({
    "council_term": ("The council's month is up.  Every seat goes back to the meeting.", "info"),
    "council_law": ("So the place will be run by a council of three.  The next meeting chooses it.", "good"),
    "council_gone": ("No more council.  Whoever spoke for it holds the chair alone, for now.", "info"),
    "council_none": ("Not enough hands go up for anyone.  The place goes on without a council for now.", "info"),
    "council_chosen": ("The meeting chooses its council: <global_val:pf_cn_list>, and <global_val:pf_cn_spk>.", "good"),
    "council_rules": ("The council hears them both out: <global_val:pf_cq_a> for <global_val:pf_kd_aname>, <global_val:pf_cq_b> for <global_val:pf_kd_bname>, <global_val:pf_cq_s> for shaking on it.  It's ruled for <global_val:pf_kd_wname>, and <global_val:pf_kd_lname> doesn't say much after that.", "info"),
    "council_split": ("The council hears them both out and can't agree who's right (<global_val:pf_cq_a> for <global_val:pf_kd_aname>, <global_val:pf_cq_b> for <global_val:pf_kd_bname>, <global_val:pf_cq_s> for shaking on it).  The two of them are told to shake on it.  Eventually, they do.", "good"),
    "council_door_yes": ("The council talks it over at the door, <global_val:pf_cnv_y> to <global_val:pf_cnv_no>: they can stay.", "good"),
    "council_door_no": ("The council talks it over at the door, <global_val:pf_cnv_no> to <global_val:pf_cnv_y> against.  Not this time.", "bad"),
    "nb_council_yes": ("The council talks it over, <global_val:pf_cnv_y> to <global_val:pf_cnv_no>: yes.", "info"),
    "nb_council_no": ("The council talks it over, <global_val:pf_cnv_no> to <global_val:pf_cnv_y>: no.", "info"),
    "council_lost": ("<global_val:pf_cn_dead_name> is gone, and the council is a seat short.  The meeting will choose it again tomorrow evening.", "bad"),
    "who_council": ("The place is run by its council: <global_val:pf_cn_list>, and <global_val:pf_cn_spk>.  The seats come up again in <global_val:pf_km_cn_days> days.  Next meeting: <global_val:pf_km_when>.", "info"),
    "nv_coming": ("Someone is coming up the road from the <global_val:pf_nv_dir>, alone, hands where you can see them: <global_val:pf_nv_name>, from <global_val:pf_nv_from>.", "info"),
    "nv_busy": ("An envoy is already on the road.", "info"),
    "nv_leaves": ("<global_val:pf_nv_name> nods, and starts back toward <global_val:pf_nv_from>.", "info"),
    "nv_missed": ("Word reaches you: the envoy from <global_val:pf_nv_from> waited at the gate, and went home without seeing you.", "info"),
    "nv_dead": ("<global_val:pf_nv_name>, the envoy from <global_val:pf_nv_from>, is dead before they ever reached the gate.  <global_val:pf_nv_from> will hear of it.", "bad"),
    "nb_match_nobody": ("<global_val:pf_cur_lead> asks after a match between the two places, but there's nobody here free to marry.  Next time, maybe.", "info"),
    "nb_match_unwilling": ("<global_val:pf_cur_lead> offers a match, but nobody here who's free wants one.  The envoy takes it well enough.", "info"),
    "nb_match_yes": ("It's agreed: in two days someone comes from <global_val:pf_cur_name> to marry <global_val:pf_nb_mp_name>.  <global_val:pf_nb_mp_name> doesn't sleep much that night.", "good"),
    "nb_match_no": ("The answer goes back: no match.  <global_val:pf_cur_name> takes it as a slight.", "bad"),
    "nb_match_off": ("Someone comes from <global_val:pf_cur_name> for the wedding, and turns back at the gate: <global_val:pf_nb_mp_name> isn't free any more.", "bad"),
    "nb_match_arrive": ("Down the road from the <global_val:pf_cur_dir> comes <global_val:pf_nb_sp_name> of <global_val:pf_cur_name>, with everything they own on their back, to marry <global_val:pf_nb_mp_name>.  The wedding will be at the next evening's fire.  From now on, <global_val:pf_cur_name> is family.", "good"),
})
files["lines.json"] = [eoc("PF_SAY_keep", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Keep lines, picked by the context var 'line'.")]
files["lab_keep.json"] += [
    eoc("PF_KL_council", [m("pf_law_lord = 0"), m("pf_law_council = 1"), m("pf_law_council_t = time('now')"), m("pf_cn_n = 0"), m("pf_cn_term = value_or(pf_cn_term, 0) + 1"),
                          say("[keep lab] A council of three is law; the next meeting chooses it (no lord any more).")]),
    eoc("PF_KL_cn_elect", [{"if": m("value_or(pf_law_council, 0) == 1"), "then": [
        {"run_eocs": "PF_KEEP_count"},
        {"if": m("pf_kp_n >= 2"), "then": [{"u_location_variable": g("pf_kp_av")}, {"run_eocs": "PF_KEEP_council_election"}],
         "else": [say("[keep lab] Fewer than 2 grown-ups who live here are in range.")]}],
        "else": [say("[keep lab] The council isn't law (use the row before this).")]}], "Keep lab: the council is chosen now."),
    eoc("PF_KL_cn_door", [{"if": m(COUNCIL_ON), "then": [
        {"set_string_var": "The Testers", "target_var": g("pf_tj_name")}, m("pf_kl_dry = 1"), {"run_eocs": "PF_KEEP_council_door"}, m("pf_kl_dry = 0"),
        say("[keep lab] (dry run: nobody moves in)  Councillors here: <global_val:pf_cnv_here>.")],
        "else": [say("[keep lab] There's no council.")]}], "Keep lab: a family at the door, for the council (a dry run)."),
    eoc("PF_KL_cn_stats", [{"if": m(COUNCIL_ON), "then": [{"run_eocs": "PF_KEEP_cn_list"}, {"run_eocs": "PF_KEEP_cn_present"},
                                                          say("[keep lab] council: <global_val:pf_cn_list> (<global_val:pf_cn_spk>), here now <global_val:pf_cnv_here>, term <global_val:pf_cn_term>, councils chosen <global_val:pf_councils_total>, its rulings <global_val:pf_council_rulings_total>.")],
                            "else": [m("pf_hs_a = value_or(pf_law_council, 0)"), m("pf_hs_b = value_or(pf_cn_n, 0)"), say("[keep lab] No council sits (law <global_val:pf_hs_a>, seats <global_val:pf_hs_b>).")]}]),
    eoc("PF_KL_nb_match", [{"if": m("value_or(pf_st_n, 0) > 0"), "then": [m("pf_st_i = 0")] + NB_LOAD + [
        m("pf_cur_rel = max(pf_cur_rel, 60)"), m("pf_cur_pact = 2"), m("pf_st_allied = 1"), {"copy_var": g("pf_cur_name"), "target_var": g("pf_st_ally_name")}, m("pf_cur_kin = 0"), m("pf_cur_trib = 0")] + NB_STORE + [
        m("pf_kl_nb_match = 1"), m("pf_nb_mpend = 0"), m("pf_st_rot = pf_st_n - 1"),
        say("[keep lab] <global_val:pf_cur_name> is close and agreed with you; their next envoy (t) offers a match.")],
        "else": [say("[keep lab] Nobody knows of the place yet.")]}]),
    eoc("PF_KL_nb_agree", [{"if": m("value_or(pf_st_n, 0) > 0"), "then": [
        m("pf_kl_ag = 0"),
        {"u_run_npc_eocs": [{"id": "PF_KL_nb_agree_one", "condition": {"and": [ADULT_RES, m("value_or(u_pf_has_sweet, 0) == 0"), m("pf_kl_ag == 0")]},
                             "effect": [m("pf_kl_ag = 1"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_nb_mp_uid")}, name_into("pf_nb_mp_name"),
                                        m("pf_nb_mp_or = value_or(u_pf_orient, 2)"), m("u_pf_rom = 1")]}], "local": True, "npc_range": 30},
        {"if": m("pf_kl_ag == 1"),
         "then": [m("pf_st_i = 0"), m("pf_nb_mpend = 1"), m("pf_nb_mst = 0"), m(f"pf_nb_mday = {TODAY}"),
                  say("[keep lab] A match is agreed for <global_val:pf_nb_mp_name> (the first settlement's; 'the one from the other place arrives now' brings them).")],
         "else": [say("[keep lab] No grown-up without a partner who lives here within 30 tiles.")]}],
        "else": [say("[keep lab] Nobody knows of the place yet.")]}],
        "Keep lab: skips the offer: the nearest free grown-up who lives here is promised to the first settlement's match (made open to romance if they weren't)."),
    eoc("PF_KL_nb_wed", [{"if": m("value_or(pf_nb_mpend, 0) == 1"), "then": [{"run_eocs": "PF_NB_match_arrive"}], "else": [say("[keep lab] No match is agreed.")]}],
        "Keep lab: the one from the other place arrives now."),
    eoc("PF_KL_acquaint", [
        {"u_run_npc_eocs": [{"id": "PF_KL_acq_a", "condition": ADULT_RES, "effect": [
            {"u_set_talker": g("pf_kl_acq")}, {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kl_acq_uid")},
            m("pf_m_str_in = 100"), {"run_eocs": "PF_MK_shared_danger", "beta_talker": "avatar"},
            {"u_run_npc_eocs": [{"id": "PF_KL_acq_b", "condition": {"and": [ADULT_RES, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kl_acq_uid")]}}]}, "effect": [
                m("pf_m_str_in = 100"), {"run_eocs": "PF_MK_shared_danger", "alpha_talker": g("pf_kl_acq"), "beta_talker": "u"}]}], "local": True, "npc_range": 60}]}],
         "local": True, "npc_range": 60},
        say("[keep lab] Everyone who lives here has been through something together, you included (shared danger, each pair).")],
        "Keep lab: everyone who lives here gets to know each other (and you)."),    eoc("PF_KL_nv_door", [{"if": m("value_or(pf_nv_state, 0) == 1"), "then": [by_uid([{"id": "PF_KL_nv_tp", "effect": [{"u_teleport": g("pf_nv_door"), "force_safe": True}]}], g("pf_nv_uid")),
                                                                               say("[keep lab] The envoy is at the door (they speak on the next minute's tick).")],
                           "else": [say("[keep lab] No envoy is walking in.")]}]),
]

for fname, data in files.items():
    json.dump(data, open(os.path.join(OUT, fname), "w", encoding="utf-8", newline="\n"), indent=2)
print("keep written:", {k: len(v) for k, v in files.items()})
