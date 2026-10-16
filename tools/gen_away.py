"""Generates mods/PeopleFirst/away/*.json: v0.7 "Open threads" (concept section 15).

15.1 The place while you're away: data while you're away, people when you're back.  A household roll taken while
     you're home (who lives here, their jobs, the animals); "away" once you're 60+ tiles from home; one away day per
     day gone (the pantry fills by the household's jobs, the field grows, is harvested and replanted, a missed meeting
     is noted, news is kept); and the homecoming: the welcome, the news, the pantry as real items, the field's terrain,
     the days replayed among the people at home, the wounded, and the meeting that waited for you.
15.2 Danger on the road: an off-screen band may run into the dead (a scare, someone hurt and pulled out, rarely
     someone lost), as moments between its members; the rumors carry it.
Neighbor raids and deliveries while you're away (gen_keep.py) and the rumor wording (gen_home.py) call in here.

Usage:  python tools/gen_away.py mods/PeopleFirst
"""
import json, os, sys, string

ROOT = sys.argv[1]
OUT = os.path.join(ROOT, "away")
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
def line(key): return {"run_eocs": "PF_SAY_away", "alpha_talker": "avatar", "variables": {"line": key}}
def by_uid(eocs, uid): return {"u_run_npc_eocs": eocs, "unique_ids": [uid], "local": False}
CALM = "value_or(pf_set_chatter, 1) == 1"
AT_HOME = "value_or(pf_home_set, 0) == 1"
AWAY = "value_or(pf_aw_state, 0) == 1"
TODAY = "floor(time('now') / time('1 d'))"
HOUR = "time_since('midnight', 'unit': 'hours')"
ADULT = {"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18")]}
GROW_DAYS = "(value_or(pf_set_grow, 1) == 0 ? 90 : (value_or(pf_set_grow, 1) == 1 ? 30 : 2))"
def count_at_home(mon): return f"monsters_nearby('{mon}', 'radius': 25, 'location': pf_home_loc, 'attitude': 'friendly')"
MEET_DAY = 2          # as in gen_keep.py
AWAY_FAR = 60         # tiles from home: out of the bubble
HOME_NEAR = 30        # tiles from home: back
NEWS_MAX = 8
ROLL_MAX = 24
REPLAY_MAX = 5
PRESENT_MAX = 12
# pass 2: whoever the raid killed is still standing at home until you're back; they're left out of the welcome and the replay
NOT_DEAD = {"not": {"and": [m("value_or(pf_aw_dead_pending, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_aw_dead_uid")]}]}}
files = {}


def news(text):
    """Effects: one line of news (text may use tags; pf_aw_dshow is the day as the sidebar shows it), up to NEWS_MAX."""
    return [{"if": m(f"value_or(pf_aw_news_n, 0) < {NEWS_MAX}"), "then": [
        {"set_string_var": "pf_aw_news_<global_val:pf_aw_news_n>", "target_var": ctx("nk"), "parse_tags": True},
        {"set_string_var": text, "target_var": {"var_val": "nk"}, "parse_tags": True},
        m("pf_aw_news_n = value_or(pf_aw_news_n, 0) + 1")]}]



# full run day 183: "While you were away: Day 184: the field came in." while the sidebar said "Autumn, day 2".  News dates
# are written the way the sidebar shows them (91-day seasons).
def when_eff(out="pf_aw_dwhen", src="pf_aw_dshow"):
    return [m(f"_wd = {src} - 1"), m("_ws = floor((_wd % 364) / 91)"), m("pf_aw_wday = (_wd % 91) + 1")] + [
        {"if": m(f"_ws == {i}"), "then": [{"set_string_var": f"{name}, day <global_val:pf_aw_wday>", "target_var": g(out), "parse_tags": True}]}
        for i, name in enumerate(["Spring", "Summer", "Autumn", "Winter"])]

# ============================================================ 15.1 THE PLACE WHILE YOU'RE AWAY
PANTRY = ["pf_pn_soup", "pf_pn_water", "pf_pn_forage", "pf_pn_eggs", "pf_pn_harvest", "pf_pn_del_0", "pf_pn_del_1", "pf_pn_del_2",
          "pf_aw_field_redo", "pf_aw_meet_missed", "pf_aw_wall_n", "pf_aw_meet_dshow"]
files["away.json"] = [
    eoc("PF_AW_tick", [
        {"u_location_variable": g("pf_aw_av")}, m("pf_aw_d = distance(pf_aw_av, pf_home_loc)"),
        {"if": m(AWAY),
         # every full day gone counts before the homecoming (a quick walk back could skip the last one)
         "then": [m("pf_aw_due = floor((time('now') - pf_aw_since) / time('1 d'))"),
                  {"run_eocs": "PF_AW_day", "condition": m("pf_aw_days_done < pf_aw_due"), "iterations": 60},
                  {"if": m(f"pf_aw_d <= {HOME_NEAR}"), "then": [{"run_eocs": "PF_AW_return"}]}],
         "else": [{"if": m(f"pf_aw_d > {AWAY_FAR}"),
                   "then": [{"run_eocs": "PF_AW_leave"}],
                   "else": [{"if": m(f"(pf_aw_d <= {HOME_NEAR}) * (time('now') - value_or(pf_hh_t, 0) >= time('30 m'))"), "then": [{"run_eocs": "PF_AW_roll"}]}]}]},
    ], "Every 10 minutes while you have a home: at home (within 30 tiles), the household roll every 30 minutes; more than 60 tiles out, you're away; away, one away day per full day gone; back within 30 tiles, the homecoming.  Only math and your own position: nothing here touches the map at home while you're gone.",
        recurrence="10 minutes", **{"global": True}, condition=m(AT_HOME)),
    eoc("PF_AW_roll", [
        m("pf_hh_t = time('now')"),
        m("pf_hh_n = 0"), m("pf_hh_adults = 0"), m("pf_hh_kids = 0"), m("pf_hh_cooks = 0"), m("pf_hh_foragers = 0"),
        {"u_run_npc_eocs": ["PF_AW_roll_one"], "local": True, "npc_range": 60},
        {"if": m("value_or(pf_aw_dead_pending, 0) == 1"), "then": [{"run_eocs": "PF_AW_bury_scan"}]},
        m("pf_hh_cows = " + count_at_home("mon_cow")), m("pf_hh_goats = " + count_at_home("mon_goat")), m("pf_hh_hens = " + count_at_home("mon_chicken")),
    ], "u = avatar, home.  Who lives here (uid, name, grown-up or child, job counts) and the animals, for while you're away (pf_hh_*)."),
    eoc("PF_AW_roll_one", [
        {"set_string_var": "pf_hh_uid_<global_val:pf_hh_n>", "target_var": ctx("ru"), "parse_tags": True},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "ru"}},
        {"set_string_var": "pf_hh_nm_<global_val:pf_hh_n>", "target_var": ctx("rn"), "parse_tags": True},
        {"set_string_var": "<u_name>", "target_var": {"var_val": "rn"}, "parse_tags": True},
        {"set_string_var": "pf_hh_ad_<global_val:pf_hh_n>", "target_var": ctx("ra"), "parse_tags": True},
        {"if": ADULT,
         "then": [m("v_ra = 1"), m("pf_hh_adults += 1"),
                  {"if": m("value_or(u_pf_role, 0) == 1"), "then": [m("pf_hh_cooks += 1")]},
                  {"if": m("value_or(u_pf_role, 0) == 3"), "then": [m("pf_hh_foragers += 1")]}],
         "else": [m("v_ra = 0"), m("pf_hh_kids += 1")]},
        m("pf_hh_n += 1"),
    ], "u = someone who lives here.",
        condition={"and": [m("value_or(u_pf_resident, 0) == 1"), m("has_var(u_pf_uid)"), m(f"pf_hh_n < {ROLL_MAX}")]}),
    eoc("PF_AW_leave", [
        # playtest: loaded the save and left within ten minutes, before any roll: the place looked empty while you were gone
        {"if": m("time('now') - value_or(pf_hh_t, 0) >= time('1 d')"), "then": [
            {"run_eocs": "PF_AW_roll"},
            {"if": m("(pf_hh_n == 0) * (value_or(pf_residents_n, 0) > 0)"), "then": [
                m("pf_hh_n = pf_residents_n"), m("pf_hh_adults = pf_residents_n"), m("pf_hh_cooks = 1")]}]},
        m("pf_aw_state = 1"), m("pf_aw_since = time('now')"), m("pf_aw_days_done = 0"), m("pf_aw_news_n = 0"),
    ] + [m(f"{v} = 0") for v in PANTRY] + [
        {"set_string_var": "none", "target_var": g("pf_aw_hurt_uid")},
        m("pf_aw_leaves_total = value_or(pf_aw_leaves_total, 0) + 1"),
    ], "u = avatar, now more than 60 tiles from home.  From here the place is data until you're back."),
    eoc("PF_AW_day", [
        m("pf_aw_days_done += 1"), m("pf_aw_dno = floor(pf_aw_since / time('1 d')) + pf_aw_days_done"), m("pf_aw_dshow = pf_aw_dno + 1"), *when_eff(),
        {"if": m("value_or(pf_hh_n, 0) > 0"), "then": [
            {"if": m("value_or(pf_hh_cooks, 0) > 0"), "then": [m("pf_pn_soup = min(pf_pn_soup + 2, 6)")]},
            m("pf_pn_water = min(pf_pn_water + 8, 16)"),
            {"if": m("value_or(pf_hh_foragers, 0) > 0"), "then": [m("pf_pn_forage = min(pf_pn_forage + 1, 4)")]},
            m("pf_pn_eggs = min(pf_pn_eggs + floor((value_or(pf_hh_hens, 0) + 1) / 2), 12)"),
            m("pf_stores = value_or(pf_stores, 0) + value_or(pf_hh_cows, 0) + value_or(pf_hh_goats, 0) + floor(value_or(pf_hh_hens, 0) / 4) + (value_or(pf_hh_adults, 0) >= 2)"),
            # the field (gen_town.py): harvested when grown, planted again in season
            {"if": m(f"(value_or(pf_field_state, 0) == 2) * (time('now') - value_or(pf_field_t, 0) >= time('1 d') * {GROW_DAYS})"),
             "then": [m("pf_field_state = 1"), m("pf_harvest_day = pf_aw_dno"), m("pf_stores = value_or(pf_stores, 0) + 20"),
                      m("pf_harvests_total = value_or(pf_harvests_total, 0) + 1"), m("pf_pn_harvest = 1"), m("pf_aw_field_redo = 1")]
                     + news("<global_val:pf_aw_dwhen>: the field came in.  Potatoes, carrots, cabbages: the stores are full."),
             "else": [{"if": {"and": [m("value_or(pf_field_state, 0) == 1"), m("value_or(pf_hh_adults, 0) > 0"), {"or": [{"is_season": "spring"}, {"is_season": "summer"}]}]},
                       "then": [m("pf_field_state = 2"), m("pf_field_t = time('now')"), m("pf_plantings_total = value_or(pf_plantings_total, 0) + 1"),
                                m("pf_aw_field_redo = 1")] + news("<global_val:pf_aw_dwhen>: they planted the field again.")}]},
            {"if": m(f"(pf_aw_dno % 7 == {MEET_DAY}) * (value_or(pf_meetings_total, 0) > 0)"), "then": [
                {"if": m("pf_aw_meet_missed == 0"), "then": [m("pf_aw_meet_dshow = pf_aw_dshow"), {"copy_var": g("pf_aw_dwhen"), "target_var": g("pf_aw_meet_dwhen")}]}, m("pf_aw_meet_missed = 1")]},
            # pass 2: the wall goes on going up (a side a day with 2+ grown-ups, not on the rest day); the map catches up when you're back
            {"if": m(f"(value_or(pf_wall_state, 0) == 1) * (value_or(pf_hh_adults, 0) >= 2) * (value_or(pf_wall_side, 0) + pf_aw_wall_n < 4) * ((value_or(pf_law_rest, 0) == 1) * (pf_aw_dno % 7 == {MEET_DAY}) == 0)"), "then": [
                m("pf_aw_wall_n += 1"), m("pf_aw_wk = value_or(pf_wall_side, 0) + pf_aw_wall_n")] +
                [{"if": m(f"pf_aw_wk == {k}"), "then": [{"set_string_var": nm, "target_var": g("pf_aw_wname")}]} for k, nm in ((1, "north"), (2, "east"), (3, "south"), (4, "west"))] +
                news("<global_val:pf_aw_dwhen>: the <global_val:pf_aw_wname> side of the wall went up.")}]},
        m("pf_aw_days_total = value_or(pf_aw_days_total, 0) + 1"),
    ], "u = avatar, away.  One day at home, as data: the pantry fills by the household's jobs (a cook's pot, water, the forager's finds, eggs by the last count; capped, since only you eat), the stores grow, the field is harvested when grown and planted again in season (its terrain catches up when you're back), and a missed meeting day is noted."),
    # -------- neighbors while you're away (called from gen_keep.py)
    eoc("PF_AW_delivery", [
        m("pf_aw_dshow = " + TODAY + " + 1"), *when_eff(),
        {"if": m("pf_cur_kind == 0"), "then": [m("pf_pn_del_0 = min(pf_pn_del_0 + 1, 2)")]},
        {"if": m("pf_cur_kind == 1"), "then": [m("pf_pn_del_1 = min(pf_pn_del_1 + 1, 2)")]},
        {"if": m("pf_cur_kind == 2"), "then": [m("pf_pn_del_2 = min(pf_pn_del_2 + 1, 2)")]},
    ] + news("<global_val:pf_aw_dwhen>: carts came from <global_val:pf_cur_name>, as agreed."),
        "u = avatar, current settlement (gen_keep.py PF_NB_upkeep), while you're away: the week's goods wait in the pantry instead of being dropped on an unloaded map."),
    eoc("PF_AW_raid_news", [
        m("pf_aw_dshow = " + TODAY + " + 1"), *when_eff(),
        {"if": m("pf_aw_raid_held == 1"),
         "then": news("<global_val:pf_aw_dwhen>: raiders from <global_val:pf_cur_name> tried the place in the night.  They were driven off."),
         "else": [
            # pass 2: badly outnumbered (by 3 or more), one time in two someone grown-up doesn't live through it
            {"if": m("(value_or(pf_nb_att, 0) - value_or(pf_nb_def, 0) >= 3) * ((rand(1) == 0) + value_or(pf_aw_force_death, 0) > 0) * (value_or(pf_aw_dead_pending, 0) == 0)"),
             "then": [{"run_eocs": "PF_AW_raid_wound"}],
             "else": [m("pf_aw_wf = 0"), {"if": m("rand(1) == 0"), "then": [{"run_eocs": "PF_AW_raid_wound"}]}, m("pf_aw_wf = pf_aw_wf * 2")]},
            {"if": m("pf_aw_wf == 1"), "then": [
                {"copy_var": g("pf_aw_hurt_uid"), "target_var": g("pf_aw_dead_uid")}, {"copy_var": g("pf_aw_hurt_name"), "target_var": g("pf_aw_dead_name")},
                {"set_string_var": "none", "target_var": g("pf_aw_hurt_uid")}, m("pf_aw_dead_pending = 1")]
                + news("<global_val:pf_aw_dwhen>: raiders from <global_val:pf_cur_name> got in and took <global_val:pf_nb_took> of the stores.  <global_val:pf_aw_dead_name> was killed holding the door.  They buried <global_val:pf_aw_dead_name> behind the place the next morning.")},
            {"if": m("pf_aw_wf == 2"), "then": news("<global_val:pf_aw_dwhen>: raiders from <global_val:pf_cur_name> got in and took <global_val:pf_nb_took> of the stores.  <global_val:pf_aw_hurt_name> was hurt trying to stop them.")},
            {"if": m("pf_aw_wf == 0"), "then": news("<global_val:pf_aw_dwhen>: raiders from <global_val:pf_cur_name> got in and took <global_val:pf_nb_took> of the stores.")}]},
    ], "u = avatar, current settlement (gen_keep.py PF_NB_raid), while you're away.  pf_aw_raid_held: 1 driven off, 0 got through."),
    eoc("PF_AW_raid_wound", [
        m("pf_aw_wf = 0"), m("pf_aw_wt = 0"),
        {"run_eocs": "PF_AW_raid_wound_try", "condition": m("(pf_aw_wf == 0) * (pf_aw_wt < 12) * (value_or(pf_hh_n, 0) > 0)"), "iterations": 13},
    ], "u = avatar.  Picks someone grown-up on the roll (pf_aw_hurt_uid/name; pf_aw_wf = 1 if anyone).  The caller decides whether they're hurt or killed; either waits for your return."),
    eoc("PF_AW_raid_wound_try", [
        m("pf_aw_wt += 1"), m("pf_aw_wi = rand(pf_hh_n - 1)"),
        {"set_string_var": "pf_hh_ad_<global_val:pf_aw_wi>", "target_var": ctx("ra"), "parse_tags": True},
        {"if": m("value_or(v_ra, 0) == 1"), "then": [
            m("pf_aw_wf = 1"),
            {"set_string_var": "pf_hh_uid_<global_val:pf_aw_wi>", "target_var": ctx("ru"), "parse_tags": True},
            {"copy_var": {"var_val": "ru"}, "target_var": g("pf_aw_hurt_uid")},
            {"set_string_var": "pf_hh_nm_<global_val:pf_aw_wi>", "target_var": ctx("rn"), "parse_tags": True},
            {"copy_var": {"var_val": "rn"}, "target_var": g("pf_aw_hurt_name")}]},
    ]),
    # -------- coming home
    eoc("PF_AW_return", [
        m("pf_aw_state = 0"), m("pf_aw_back_t = time('now')"),
        m("pf_aw_gone_h = floor((time('now') - pf_aw_since) / time('1 h'))"), m("pf_aw_gone_d = floor(pf_aw_gone_h / 24)"),
        {"if": m("(pf_aw_gone_h >= 12) + (value_or(pf_aw_news_n, 0) > 0) > 0"), "then": [{"run_eocs": "PF_AW_home"}]},
        m("pf_hh_t = 0"),
    ], "u = avatar, back within 30 tiles of home.  Half a day or more, or news from a shorter trip (a raid in the night): the homecoming."),
    eoc("PF_AW_home", [
        {"set_string_var": "<global_val:pf_aw_gone_d> days", "target_var": g("pf_aw_gone_t"), "parse_tags": True},
        {"if": m("pf_aw_gone_d == 1"), "then": [{"set_string_var": "a day", "target_var": g("pf_aw_gone_t")}]},
        {"if": m("pf_aw_gone_d < 1"), "then": [{"set_string_var": "half a day", "target_var": g("pf_aw_gone_t")}]},
        # the welcome (not for a night's errand that only brought news)
        m("pf_aw_gbest = -1"),
        {"if": m("pf_aw_gone_h >= 12"), "then": [
            {"u_run_npc_eocs": ["PF_AW_greet_cand"], "local": True, "npc_range": 40},
            {"if": m("pf_aw_gbest >= 0"), "then": [{"run_eocs": "PF_AW_greet", "alpha_talker": g("pf_aw_greeter"), "beta_talker": "avatar"}],
             "else": [{"if": m("value_or(pf_hh_n, 0) > 0"), "then": [line("welcome_none")]}]}]},
        # the news
        {"if": m("value_or(pf_aw_news_n, 0) > 0"), "then": [line("news_head")] + [
            {"if": m(f"pf_aw_news_n > {i}"), "then": [say(f"<global_val:pf_aw_news_{i}>")]} for i in range(NEWS_MAX)]},
        # pass 2: a baby that came due while you were gone is there when you get back (gen_family.py PF_FAM_birth reads pf_aw_birthing)
        {"if": m("pf_aw_gone_h >= 12"), "then": [m("pf_aw_birthing = 1"), {"run_eocs": "PF_FAM_preg_tick"}, m("pf_aw_birthing = 0")]},
        # pass 2: whoever the raid killed is in the ground behind the place
        {"run_eocs": "PF_AW_bury_scan"},
        # the pantry, as real things at home
        {"run_eocs": "PF_AW_pantry"},
        # pass 2: the sides of the wall that went up while you were gone (quietly; the last one still says so)
        {"if": m("pf_aw_wall_n > 0"), "then": [m("pf_aw_quiet = 1"), m("pf_aw_wi2 = 0"),
            {"run_eocs": {"id": "PF_AW_wall_one", "effect": [m("pf_aw_wi2 += 1"), {"run_eocs": "PF_KEEP_wall_side"}]},
             "condition": m("(pf_aw_wi2 < pf_aw_wall_n) * (value_or(pf_wall_state, 0) == 1)"), "iterations": 5},
            m("pf_aw_quiet = 0")]},
        # the field's terrain catches up
        {"if": m("pf_aw_field_redo == 1"), "then": [
            {"if": m("value_or(pf_field_state, 0) == 2"), "then": [{"u_transform_radius": 2, "ter_furn_transform": "PF_TOWN_t_plant", "target_var": g("pf_field_loc")}]},
            {"if": m("value_or(pf_field_state, 0) == 1"), "then": [{"u_transform_radius": 2, "ter_furn_transform": "PF_TOWN_t_harvest", "target_var": g("pf_field_loc")}]}]},
        # the days, replayed among the people at home
        {"if": m("pf_aw_gone_h >= 12"), "then": [{"run_eocs": "PF_AW_replay"}]},
        # the wounded
        {"if": {"not": {"compare_string": [g("pf_aw_hurt_uid"), "none"]}}, "then": [
            m("pf_aw_hf = 0"),
            {"u_run_npc_eocs": [{"id": "PF_AW_hurt_find", "condition": {"and": [m("has_var(u_pf_uid)"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_aw_hurt_uid")]}]},
                                 "effect": [m("pf_aw_hf = 1"), name_into("pf_say_a"), m("pf_m_str_in = 50"), {"run_eocs": "PF_MK_near_death"}]}], "local": True, "npc_range": 60},
            {"if": m("pf_aw_hf == 1"), "then": [line("hurt_back")]}]},
        # the meeting: an NPC chief held it without you (pass 2: their meeting, told as it went); otherwise it waited for you
        {"if": m("(pf_aw_meet_missed == 1) * (value_or(pf_meetings_total, 0) > 0)"), "then": [
            {"if": m("value_or(pf_chief_set, 0) == 1"),
             "then": [line("meeting_held"), {"run_eocs": "PF_KEEP_agenda"}],
             "else": [m("pf_mt_due = 1"), line("meeting_waited")]}]},
        m("pf_aw_returns_total = value_or(pf_aw_returns_total, 0) + 1"),
    ] + [m(f"{v} = 0") for v in PANTRY] + [
        m("pf_aw_news_n = 0"), {"set_string_var": "none", "target_var": g("pf_aw_hurt_uid")},
    ], "u = avatar.  The homecoming (concept 15.1): the welcome, the news, the pantry, the field, the days replayed, the wounded, the meeting."),
    eoc("PF_AW_greet_cand", [
        {"run_eocs": "PF_ID_ensure"},
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        m("_s = pf_read_w + 10 * (value_or(u_pf_resident, 0) == 1)"),
        {"if": m("(_s >= 20) * (_s > pf_aw_gbest)"), "then": [m("pf_aw_gbest = _s"), {"u_set_talker": g("pf_aw_greeter")}]},
    ], "u = someone near home.  Whoever cares most about you (warmth 20+, living here counts) meets you first.",
        condition={"and": [ADULT, m("has_var(u_pf_uid)"), {"not": {"u_has_effect": "sleep"}}, NOT_DEAD]}),
    eoc("PF_AW_greet", [
        name_into("pf_say_a"),
        {"if": m("pf_aw_gone_d >= 7"), "then": [line("welcome_long"), m("pf_m_str_in = 60")],
         "else": [{"if": m("pf_aw_gone_d >= 3"), "then": [line("welcome_mid"), m("pf_m_str_in = 50")],
                   "else": [line("welcome_short"), m("pf_m_str_in = 40")]}]},
        {"run_eocs": "PF_MK_welcomed_back"},
    ], "Alpha = the one who meets you, beta = you.  Words by how long you were gone; a welcomed_back moment (stronger the longer you were away)."),
    eoc("PF_AW_pantry", [
        m("pf_aw_got = 0"),
        # a bowl holds 2 servings and a jug 8 (more in one container is an error: "pocket unacceptable")
        {"if": m("pf_pn_soup > 0"), "then": [m("pf_aw_got = 1"), m("pf_aw_bi = 0"),
            {"run_eocs": {"id": "PF_AW_bowl", "effect": [m("pf_aw_bi += 1"), {"map_spawn_item": "soup_veggy", "loc": g("pf_stores_loc"), "container": "ceramic_bowl", "count": 2}]},
             "condition": m("pf_aw_bi < pf_pn_soup / 2"), "iterations": 4}]},
        {"if": m("pf_pn_water > 0"), "then": [m("pf_aw_bi = 0"),
            {"run_eocs": {"id": "PF_AW_jug", "effect": [m("pf_aw_bi += 1"), {"map_spawn_item": "water_clean", "loc": g("pf_stores_loc"), "container": "jug_plastic", "count": 8}]},
             "condition": m("pf_aw_bi < pf_pn_water / 8"), "iterations": 3}]},
        {"if": m("pf_pn_eggs > 0"), "then": [m("pf_aw_got = 1"), {"map_spawn_item": "egg_chicken", "loc": g("pf_stores_loc"), "count": g("pf_pn_eggs")}]},
        {"if": m("pf_pn_forage > 0"), "then": [m("pf_aw_got = 1"), m("pf_aw_n = 3 * pf_pn_forage"),
            {"map_spawn_item": "blueberries", "loc": g("pf_stores_loc"), "count": g("pf_aw_n")},
            {"map_spawn_item": "mushroom", "loc": g("pf_stores_loc"), "count": g("pf_pn_forage")}]},
        {"if": m("pf_pn_harvest > 0"), "then": [m("pf_aw_got = 1"),
            {"map_spawn_item": "potato", "loc": g("pf_stores_loc"), "count": 12},
            {"map_spawn_item": "carrot", "loc": g("pf_stores_loc"), "count": 10},
            {"map_spawn_item": "cabbage_head", "loc": g("pf_stores_loc"), "count": 4}]},
        # the neighbors' deliveries (gen_keep.py PF_NB_upkeep), as they would have come
        {"if": m("pf_pn_del_2 > 0"), "then": [m("pf_aw_got = 1"), m("pf_aw_n = 3 * pf_pn_del_2"), m("pf_aw_n2 = 5 * pf_pn_del_2"),
            {"map_spawn_item": "pemmican", "loc": g("pf_stores_loc"), "count": g("pf_aw_n")},
            {"map_spawn_item": "seed_potato_raw", "loc": g("pf_stores_loc"), "count": g("pf_aw_n2")}]},
        {"if": m("pf_pn_del_1 > 0"), "then": [m("pf_aw_got = 1"), m("pf_aw_n = 10 * pf_pn_del_1"), m("pf_aw_n2 = 5 * pf_pn_del_1"),
            {"map_spawn_item": "aspirin", "loc": g("pf_stores_loc"), "count": g("pf_aw_n")},
            {"map_spawn_item": "bandages", "loc": g("pf_stores_loc"), "count": g("pf_aw_n2")}]},
        {"if": m("pf_pn_del_0 > 0"), "then": [m("pf_aw_got = 1"), m("pf_aw_n = 10 * pf_pn_del_0"),
            {"map_spawn_item": "bolt_metal", "loc": g("pf_stores_loc"), "count": g("pf_aw_n")}]},
        {"if": m("pf_aw_got == 1"), "then": [line("pantry")]},
    ], "u = avatar, home.  What the place put by while you were away, as real items at home."),
    eoc("PF_AW_replay", [
        m("pf_aw_pn = 0"), m("pf_aw_ri = 0"), m("pf_aw_warm = 0"), m("pf_aw_tense = 0"), m("pf_aw_met = 0"),
        {"u_run_npc_eocs": [{"id": "PF_AW_present", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), m("has_var(u_pf_uid)"), m(f"pf_aw_pn < {PRESENT_MAX}"), NOT_DEAD]},
                             "effect": [{"set_string_var": "pf_aw_p_<global_val:pf_aw_pn>", "target_var": ctx("pu"), "parse_tags": True},
                                        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "pu"}}, m("pf_aw_pn += 1")]}], "local": True, "npc_range": 60},
        m(f"pf_aw_rd = min(max(pf_aw_gone_d, 1), {REPLAY_MAX})"),
        {"if": m("pf_aw_pn >= 2"), "then": [
            {"run_eocs": "PF_AW_replay_one", "condition": m("pf_aw_ri < pf_aw_rd"), "iterations": REPLAY_MAX + 1},
            {"if": m("pf_aw_warm == 1"), "then": [line("days_warm")]},
            {"if": m("pf_aw_tense == 1"), "then": [line("days_tense")]},
            {"if": m("(pf_aw_warm == 0) * (pf_aw_tense == 0) * (pf_aw_met == 1)"), "then": [line("days_met")]}]},
    ], "u = avatar.  For each day you were gone (up to 5), two of the grown-ups at home live a small day together, from their own views: warm pairs share evenings, tense ones bicker, strangers get to know each other.  The first warm and the first tense pair are told."),
    eoc("PF_AW_replay_one", [
        m("pf_aw_ri += 1"),
        m("pf_aw_ia = rand(pf_aw_pn - 1)"), m("pf_aw_ib = rand(pf_aw_pn - 2)"), {"if": m("pf_aw_ib >= pf_aw_ia"), "then": [m("pf_aw_ib += 1")]},
        {"set_string_var": "pf_aw_p_<global_val:pf_aw_ia>", "target_var": ctx("ra"), "parse_tags": True}, {"copy_var": {"var_val": "ra"}, "target_var": g("pf_aw_ua")},
        {"set_string_var": "pf_aw_p_<global_val:pf_aw_ib>", "target_var": ctx("rb"), "parse_tags": True}, {"copy_var": {"var_val": "rb"}, "target_var": g("pf_aw_ub")},
        m("pf_aw_fa = 0"), m("pf_aw_fb = 0"),
        {"u_run_npc_eocs": [{"id": "PF_AW_rp_a", "condition": {"and": [m("has_var(u_pf_uid)"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_aw_ua")]}]},
                             "effect": [m("pf_aw_fa = 1"), {"u_set_talker": g("pf_aw_ta")}]},
                            {"id": "PF_AW_rp_b", "condition": {"and": [m("has_var(u_pf_uid)"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_aw_ub")]}]},
                             "effect": [m("pf_aw_fb = 1"), {"u_set_talker": g("pf_aw_tb")}]}], "local": True, "npc_range": 60},
        {"if": m("pf_aw_fa * pf_aw_fb == 1"), "then": [{"run_eocs": "PF_AW_pair", "alpha_talker": g("pf_aw_ta"), "beta_talker": g("pf_aw_tb")}]},
    ], "u = avatar.  One replayed day: two different grown-ups at home (found this turn, so the stored talkers are fresh)."),
    eoc("PF_AW_pair", [
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        m("pf_m_str_in = 30"),
        {"if": m("pf_read_x >= 25"),
         "then": [{"run_eocs": "PF_MK_bicker"},
                  {"if": m("pf_aw_tense == 0"), "then": [m("pf_aw_tense = 1"), name_into("pf_aw_tn_a"), name_into("pf_aw_tn_b", "<npc_name>")]}],
         "else": [{"if": m("pf_read_w >= 15"),
                   "then": [{"run_eocs": "PF_MK_fire_evening"},
                            {"if": m("pf_aw_warm == 0"), "then": [m("pf_aw_warm = 1"), name_into("pf_aw_wm_a"), name_into("pf_aw_wm_b", "<npc_name>")]}],
                   "else": [{"run_eocs": "PF_MK_meal_shared"},
                            {"if": m("pf_aw_met == 0"), "then": [m("pf_aw_met = 1"), name_into("pf_aw_mt_a"), name_into("pf_aw_mt_b", "<npc_name>")]}]}]},
    ], "Alpha = one of them, beta = the other.  From alpha's view of beta: tension 25+ bicker, warmth 15+ an evening together, else a shared meal."),
]

files["away.json"] += [
    eoc("PF_AW_bury_scan", [
        m("pf_aw_df = 0"),
        {"u_run_npc_eocs": [{"id": "PF_AW_bury_find", "condition": {"and": [m("has_var(u_pf_uid)"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_aw_dead_uid")]}]},
                             "effect": [m("pf_aw_df = 1"), {"run_eocs": "PF_AW_bury"}]}], "local": True, "npc_range": 60},
        {"if": m("pf_aw_df == 1"), "then": [m("pf_aw_dead_pending = 0"), m("pf_unburied = 0"),
                                            {"if": m("pf_aw_grave_ok == 1"), "then": [line("grave")], "else": [line("grave_none")]}]},
    ], "u = avatar (pass 2).  Whoever a raid killed while you were away: found at home, they're in the ground (a fresh grave near where they stood) and the death is real now.  The death hooks bring the grief; the burial already happened (pf_unburied = 0), so the mourning goes on at the fire."),
    eoc("PF_AW_bury", [
        m("pf_aw_grave_ok = 0"),
        {"u_location_variable": g("pf_aw_grave"), "terrain": "t_dirt", "target_max_radius": 12, "min_radius": 2,
         "true_eocs": [{"id": "PF_AW_dig", "effect": [m("pf_aw_grave_ok = 1"), {"u_transform_radius": 0, "ter_furn_transform": "PF_AW_t_grave", "target_var": g("pf_aw_grave")}]}],
         "false_eocs": [{"id": "PF_AW_dig_grass", "effect": [
             {"u_location_variable": g("pf_aw_grave"), "terrain": "t_grass", "target_max_radius": 12, "min_radius": 2,
              "true_eocs": ["PF_AW_dig"]}]}]},
        m("u_pf_aw_buried = 1"),
        {"u_die": {"remove_corpse": True, "supress_message": True}},
    ], "u = the one the raid killed (pass 2).  A fresh grave on bare dirt or grass near them, then they're gone (no corpse, no message: the news told it)."),
    {"type": "ter_furn_transform", "id": "PF_AW_t_grave", "terrain": [{"result": "t_grave_new", "valid_flags": ["DIGGABLE"]}]},
]

# ============================================================ 15.2 DANGER ON THE ROAD
def sb_gather():
    """u = band leader.  Lists the band (leader first) in global strings pf_sb_0..5 and the count in pf_sb_n (as gen_life.py)."""
    eff = [m("pf_sb_n = 1"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_sb_0")}]
    for k in range(5):
        eff.append({"if": {"not": {"compare_string": [{"u_val": f"pf_member_{k}"}, "none"]}}, "then": [
            {"set_string_var": "pf_sb_<global_val:pf_sb_n>", "target_var": ctx("ref"), "parse_tags": True},
            {"copy_var": {"u_val": f"pf_member_{k}"}, "target_var": {"var_val": "ref"}},
            m("pf_sb_n += 1")]})
    return eff
def sb_adult(idx_expr, out):
    """Effects: out = 1 if band slot idx_expr (math) is a grown-up, from the registry (pf_reg_<uid>_a)."""
    return [m(f"pf_rd_qi = {idx_expr}"),
            {"set_string_var": "pf_sb_<global_val:pf_rd_qi>", "target_var": ctx("qs"), "parse_tags": True},
            {"copy_var": {"var_val": "qs"}, "target_var": g("pf_rd_q_uid")},
            {"set_string_var": "pf_reg_<global_val:pf_rd_q_uid>_a", "target_var": ctx("qa"), "parse_tags": True},
            m(f"{out} = value_or(v_qa, 0) == 1")]
scare = []
for i in range(6):
    scare.append({"if": m(f"pf_sb_n > {max(i, 1)}"), "then": [m(f"pf_sb_self = {i}"),
                  {"u_run_npc_eocs": ["PF_SOCIAL_hunt_viewer"], "unique_ids": [g(f"pf_sb_{i}")], "local": False}]})
adults_count = [m("pf_rd_adults = 0")]
for i in range(6):
    adults_count.append({"if": m(f"pf_sb_n > {i}"), "then": sb_adult(str(i), "_ad") + [m("pf_rd_adults += _ad")]})
files["road.json"] = [
    eoc("PF_ROAD_day", [
        {"if": m("(value_or(pf_road_force, 0) == 1) + (rand(value_or(u_pf_task, 1) == 1 ? 11 : 19) == 0) > 0"), "then": [{"run_eocs": "PF_ROAD_trouble"}]},
    ], "u = an off-screen band leader, once a day (called from the band's evening, gen_life.py).  About 1 day in 12 for hunters, 1 in 20 for families on the move; never for a family at home, a family visiting you, or a band on screen.",
        condition={"and": [m("value_or(u_pf_settled, 0) == 0"), m("value_or(u_pf_online, 0) == 0"), m("value_or(u_pf_visiting, 0) == 0"), m("value_or(pf_alife_on, 1) == 1")]}),
    eoc("PF_ROAD_trouble", sb_gather() + adults_count + [
        m("pf_rd_k = rand(2) == 2 ? 2 : 1"),
        {"if": m("(pf_rd_k == 2) * (rand(9) == 0) * (pf_rd_adults >= 3)"), "then": [m("pf_rd_k = 3")]},
        {"if": m("value_or(pf_road_kind, 0) > 0"), "then": [m("pf_rd_k = pf_road_kind")]},
        {"if": m("(pf_rd_k == 3) * (pf_sb_n < 3)"), "then": [m("pf_rd_k = 2")]},
        {"if": m("(pf_rd_k == 2) * (pf_sb_n < 2)"), "then": [m("pf_rd_k = 1")]},
        # everyone was there: shared danger
        m("pf_sb_hunt_str = 60"),
    ] + scare + [
        {"if": m("pf_rd_k == 2"), "then": [{"run_eocs": "PF_ROAD_hurt"}]},
        {"if": m("pf_rd_k == 3"), "then": [{"run_eocs": "PF_ROAD_lost"}]},
        m("u_pf_trouble_t = time('now')"), m("u_pf_trouble_kind = pf_rd_k"),
        {"if": m("pf_rd_k == 1"), "then": [m("pf_road_scares = value_or(pf_road_scares, 0) + 1")]},
        {"if": m("pf_rd_k == 2"), "then": [m("pf_road_hurts = value_or(pf_road_hurts, 0) + 1")]},
        {"if": m("pf_rd_k == 3"), "then": [m("pf_road_deaths = value_or(pf_road_deaths, 0) + 1")]},
    ], "u = an off-screen band leader.  Trouble on the road (concept 15.2): everyone faced it together (shared danger 60); one time in three someone is hurt and pulled out by another (saved_life); one hurt in ten, in a band of 3+ grown-ups, someone doesn't come back.  The leader keeps the story for the rumors (u_pf_trouble_*)."),
    eoc("PF_ROAD_hurt", [
        m("pf_rd_v = rand(pf_sb_n - 1)"),
        # the saver: the next grown-up round the band from the victim
        m("pf_rd_s = -1"), m("pf_rd_j = 1"),
        {"run_eocs": "PF_ROAD_find_saver", "condition": m("(pf_rd_s < 0) * (pf_rd_j < pf_sb_n)"), "iterations": 7},
        {"set_string_var": "pf_sb_<global_val:pf_rd_v>", "target_var": ctx("vs"), "parse_tags": True}, {"copy_var": {"var_val": "vs"}, "target_var": g("pf_rd_vuid")},
        {"if": m("pf_rd_s >= 0"),
         "then": [{"set_string_var": "pf_sb_<global_val:pf_rd_s>", "target_var": ctx("ss"), "parse_tags": True}, {"copy_var": {"var_val": "ss"}, "target_var": g("pf_rd_suid")}],
         "else": [{"set_string_var": "none", "target_var": g("pf_rd_suid")}]},
        by_uid(["PF_ROAD_hurt_one"], g("pf_rd_vuid")),
        {"if": {"not": {"compare_string": [g("pf_rd_suid"), "none"]}}, "then": [by_uid(["PF_ROAD_saver_one"], g("pf_rd_suid"))]},
    ], "u = the leader.  Someone in the band is hurt; the next grown-up round the band pulls them out."),
    eoc("PF_ROAD_find_saver", sb_adult("(pf_rd_v + pf_rd_j) % pf_sb_n", "_ad") + [
        {"if": m("_ad == 1"), "then": [m("pf_rd_s = (pf_rd_v + pf_rd_j) % pf_sb_n")]},
        m("pf_rd_j += 1"),
    ]),
    eoc("PF_ROAD_hurt_one", [
        m("u_hp('torso') = max(u_hp('torso') - 20, 5)"), m("u_pf_hurt_t = time('now')"),
        {"if": {"not": {"compare_string": [g("pf_rd_suid"), "none"]}}, "then": [
            {"copy_var": g("pf_rd_suid"), "target_var": g("pf_m_other")}, m("pf_mv_role = 1"), m("pf_m_str_in = 90"), {"run_eocs": "PF_MV_saved_life"}]},
    ], "u = the one hurt (off-screen, by unique id: math only).  Grateful to whoever pulled them out."),
    eoc("PF_ROAD_saver_one", [
        {"copy_var": g("pf_rd_vuid"), "target_var": g("pf_m_other")}, m("pf_mv_role = 2"), m("pf_m_str_in = 90"), {"run_eocs": "PF_MV_saved_life"},
    ], "u = the one who pulled them out (off-screen).  Protective of them from now on."),
    eoc("PF_ROAD_lost", [
        # never the leader (index 0) and never a child
        m("pf_rd_v = -1"), m("pf_rd_j = 0"),
        {"run_eocs": "PF_ROAD_pick_lost", "condition": m("(pf_rd_v < 0) * (pf_rd_j < 12)"), "iterations": 13},
        {"if": m("pf_rd_v >= 1"), "then": [
            {"set_string_var": "pf_sb_<global_val:pf_rd_v>", "target_var": ctx("vs"), "parse_tags": True}, {"copy_var": {"var_val": "vs"}, "target_var": g("pf_rd_vuid")},
            {"set_string_var": "pf_name_<global_val:pf_rd_vuid>", "target_var": ctx("vn"), "parse_tags": True},
            {"copy_var": {"var_val": "vn"}, "target_var": {"u_val": "pf_trouble_lost"}},
            by_uid(["PF_ROAD_die"], g("pf_rd_vuid"))],
         "else": [m("pf_rd_k = 2"), {"run_eocs": "PF_ROAD_hurt"}]},
    ], "u = the leader.  A grown-up who isn't the leader doesn't come back; if there's none, it's a wound instead."),
    eoc("PF_ROAD_pick_lost", [m("pf_rd_j += 1"), m("_c = 1 + rand(pf_sb_n - 2)")] + sb_adult("_c", "_ad") + [
        {"if": m("_ad == 1"), "then": [m("pf_rd_v = _c")]},
    ]),
    eoc("PF_ROAD_die", [
        m("u_pf_road_dead = 1"),
        {"u_die": {"remove_corpse": True, "supress_message": True}},
    ], "u = the one lost (off-screen, by unique id).  No body: the death hooks (character_dies) bring grief to the band, mourning and, for a leader, succession."),
]

# ============================================================ LINES
LINES = {
    "welcome_short": ("<global_val:pf_say_a> spots you first.  \"Look who it is.\"  You've been gone <global_val:pf_aw_gone_t>.", "good"),
    "welcome_mid":   ("<global_val:pf_say_a> sees you coming and walks the last bit of the way out to meet you.  \"There you are.  Gone <global_val:pf_aw_gone_t>, and not a word.  We were starting to talk about you.\"", "good"),
    "welcome_long":  ("<global_val:pf_say_a> just looks at you for a long moment.  \"We'd started to think you weren't coming back.\"  You've been gone <global_val:pf_aw_gone_t>.", "good"),
    "welcome_none":  ("Nobody makes a fuss.  The place got on without you for <global_val:pf_aw_gone_t>.", "info"),
    "news_head":     ("While you were away:", "info"),
    "pantry":        ("There's food at home: what the place put by while you were gone, set aside for you.", "good"),
    "days_warm":     ("<global_val:pf_aw_wm_a> and <global_val:pf_aw_wm_b> spent the evenings together while you were gone.  It shows.", "good"),
    "days_tense":    ("<global_val:pf_aw_tn_a> and <global_val:pf_aw_tn_b> had words more than once while you were gone.  Everyone has an opinion about it.", "bad"),
    "days_met":      ("<global_val:pf_aw_mt_a> and <global_val:pf_aw_mt_b> got to know each other a little while you were gone.", "info"),
    "hurt_back":     ("<global_val:pf_say_a> has a bandage on one arm and a story about the night the raiders came.  They tell it twice before supper.", "info"),
    "meeting_waited": ("There's a meeting tonight, now that you're back.  The last one waited for you.", "info"),
    "meeting_held":  ("On <global_val:pf_aw_meet_dwhen>, <global_val:pf_chief_name> held the meeting without you.  You hear how it went:", "info"),
    "grave":         ("<global_val:pf_aw_dead_name>'s grave is behind the place: fresh earth, and a marker with the name scratched in.  Someone has left flowers.", "bad"),
    "grave_none":    ("They buried <global_val:pf_aw_dead_name> while you were gone.  People keep starting to say the name and stopping.", "bad"),
}
files["lines.json"] = [eoc("PF_SAY_away", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Every away/homecoming line (variable 'line').")]

# ============================================================ LAB (opened from the Home lab)
def stat_say(text): return say("[away lab] " + text)
ROWS = [
    ("PF_AWL_roll", "Away: take the household roll now", "Who lives here and the animals, as the away days will see them.",
     [{"run_eocs": "PF_AW_roll"}, stat_say("roll: <global_val:pf_hh_n> people (<global_val:pf_hh_adults> grown-ups, <global_val:pf_hh_kids> children), cooks <global_val:pf_hh_cooks>, foragers <global_val:pf_hh_foragers>, hens <global_val:pf_hh_hens>, goats <global_val:pf_hh_goats>, cows <global_val:pf_hh_cows>.")]),
    ("PF_AWL_leave", "Away: leave now (as if you walked 60+ tiles off)", "Takes the roll, then you count as away; walk back within 30 tiles (or use 'come home now') for the homecoming.",
     [{"run_eocs": "PF_AW_roll"}, {"run_eocs": "PF_AW_leave"}, stat_say("You're away now (state 1).  Days pass with the next entry.")]),
    ("PF_AWL_day", "Away: one day passes at home", "Moves the time you left back by a day and runs that away day (the pantry, the field, the meeting day).",
     [{"if": m(AWAY), "then": [m("pf_aw_since -= time('1 d')"), m("pf_aw_due = floor((time('now') - pf_aw_since) / time('1 d'))"),
                               {"run_eocs": "PF_AW_day", "condition": m("pf_aw_days_done < pf_aw_due"), "iterations": 60},
                               stat_say("Day <global_val:pf_aw_days_done> away.  News <global_val:pf_aw_news_n>; pantry: soup <global_val:pf_pn_soup>, water <global_val:pf_pn_water>, eggs <global_val:pf_pn_eggs>, forage <global_val:pf_pn_forage>, harvest <global_val:pf_pn_harvest>; field <global_val:pf_field_state>.")],
       "else": [stat_say("You're not away (use 'leave now' first).")]}]),
    ("PF_AWL_raid", "Away: a raid gets through tonight", "The first settlement raids the place and gets through (needs a neighbor; the stores are topped up to 12).  While you're away it goes into the news, maybe with someone hurt.",
     [{"run_eocs": "PF_KL_nb_raid_win"}]),
    ("PF_AWL_raid_held", "Away: a raid is driven off tonight", "The first settlement raids the place (strength against defense; usually held).",
     [{"run_eocs": "PF_KL_nb_raid"}]),
    ("PF_AWL_back", "Away: come home now", "The homecoming, wherever you are (it expects you to be home: the pantry and the field are placed at home).",
     [{"if": m(AWAY), "then": [{"run_eocs": "PF_AW_return"}], "else": [stat_say("You're not away.")]}]),
    ("PF_AWL_status", "Away: status", "State, days away, news, pantry, roll and totals.",
     [m("pf_hs_a = value_or(pf_aw_state, 0)"), m("pf_hs_b = value_or(pf_aw_days_done, 0)"), m("pf_hs_c = value_or(pf_aw_news_n, 0)"),
      m("pf_hs_d = value_or(pf_aw_leaves_total, 0)"), m("pf_hs_e = value_or(pf_aw_returns_total, 0)"), m("pf_hs_f = value_or(pf_hh_n, 0)"),
      stat_say("state <global_val:pf_hs_a>, days <global_val:pf_hs_b>, news <global_val:pf_hs_c>, roll <global_val:pf_hs_f> | left <global_val:pf_hs_d> times, came back <global_val:pf_hs_e>.")]),
    ("PF_AWL_road", "Road: trouble for a band out there now", "The first band off-screen (not settled, not visiting) runs into the dead now; kind: scare, hurt or lost by the next entries' setting (default: by chance).",
     [m("pf_road_force = 1"), m("pf_rdl_i = 0"), m("pf_rdl_done = 0"),
      {"run_eocs": "PF_AWL_road_i", "condition": m("(pf_rdl_i < value_or(pf_band_n, 0)) * (pf_rdl_done == 0)"), "iterations": 200},
      m("pf_road_force = 0"),
      {"if": m("pf_rdl_done == 0"), "then": [stat_say("No band off-screen that could run into trouble.")],
       "else": [m("pf_hs_a = pf_rd_k"), stat_say("Trouble on the road for <global_val:pf_rdl_name>'s band: kind <global_val:pf_hs_a> (1 scare, 2 hurt, 3 lost).")]}]),
    ("PF_AWL_road_kind", "Road: next trouble is a scare / a wound / a loss / by chance", "Cycles the kind the next 'trouble now' uses: 1 scare, 2 hurt, 3 lost, 0 by chance.",
     [m("pf_road_kind = (value_or(pf_road_kind, 0) + 1) % 4"), m("pf_hs_a = pf_road_kind"), stat_say("Next road trouble: kind <global_val:pf_hs_a> (0 by chance, 1 scare, 2 hurt, 3 lost).")]),
    ("PF_AWL_road_stats", "Road: stats", "Scares, wounds and losses on the road so far.",
     [m("pf_hs_a = value_or(pf_road_scares, 0)"), m("pf_hs_b = value_or(pf_road_hurts, 0)"), m("pf_hs_c = value_or(pf_road_deaths, 0)"),
      stat_say("road: scares <global_val:pf_hs_a>, hurt <global_val:pf_hs_b>, lost <global_val:pf_hs_c>.")]),
    ("PF_AWL_raid_kill", "Away: a raid gets through badly tonight (someone is killed)", "As 'a raid gets through', but outnumbered and fatal: someone grown-up on the roll is killed (it waits for your return: a grave and the grief).",
     [m("pf_aw_force_death = 1"), {"run_eocs": "PF_KL_nb_raid_win"}, m("pf_aw_force_death = 0")]),
    ("PF_AWL_wall", "Away: start building the wall", "The wall goes up a side a day from tomorrow, at home or (pass 2) while you're away.",
     [{"run_eocs": "PF_KEEP_wall_start"}, m("pf_hs_a = value_or(pf_wall_state, 0)"), stat_say("wall state <global_val:pf_hs_a> (1 going up, 2 done).")]),
    ("PF_AWL_wall_half", "Away: the wall is half built again (two sides to go)", "Lab: sets the wall back to 'going up' with the north and east sides done, so the away days raise the rest (where it's open ground).",
     [m("pf_wall_state = 1"), m("pf_wall_side = 2"), stat_say("The wall is going up again: south and west to go.")]),
    ("PF_AWL_meet_missed", "Away: a meeting day was missed", "Lab: marks this week's meeting as missed while you're away (lab days don't move the weekday).  With an NPC chief it's held without you at the homecoming; otherwise it waits for you.",
     [m("pf_aw_meet_missed = 1"), m("pf_aw_meet_dshow = " + TODAY + " + 1"), m("pf_hs_a = value_or(pf_chief_set, 0)"), stat_say("Meeting missed.  Chief: <global_val:pf_hs_a> (0 none, 1 someone, 2 you).")]),
    ("PF_AWL_chief", "Away: the nearest grown-up who lives here is chief", "Lab: makes the nearest resident adult the chief (so a missed meeting is held without you).",
     [m("pf_awl_c = 0"),
      {"u_run_npc_eocs": [{"id": "PF_AWL_chief_one", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), m("has_var(u_pf_uid)"), m("pf_awl_c == 0")]},
                           "effect": [m("pf_awl_c = 1"), m("pf_chief_set = 1"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_chief_uid")},
                                      name_into("pf_chief_name"), m("pf_chief_since = time('now')")]}], "local": True, "npc_range": 30},
      {"if": m("pf_awl_c == 1"), "then": [stat_say("<global_val:pf_chief_name> is chief now.")], "else": [stat_say("Nobody grown-up who lives here within 30 tiles.")]}]),
    ("PF_AWL_due", "Away: everyone expecting here is at term (no birth yet)", "Lab: moves every pregnancy within 30 tiles to term without running the birth, so the homecoming's birth step brings the baby.",
     [m("pf_awl_c = 0"),
      {"u_run_npc_eocs": [{"id": "PF_AWL_due_one", "condition": m("value_or(u_pf_preg, 0) == 1"),
                           "effect": [m("pf_awl_c += 1"), m("u_pf_preg_t = time('now') - time('1 d') * (value_or(pf_set_grow, 1) == 0 ? 270 : (value_or(pf_set_grow, 1) == 1 ? 30 : 3)) - time('1 h')")]}],
       "local": True, "npc_range": 30},
      stat_say("<global_val:pf_awl_c> pregnancies at term.")]),
    # 15.3 children and loss, 15.4 the tense evening
    ("PF_AWL_loss", "Loss: the nearest child's mother (or father) dies now", "A child within 30 tiles whose mother or father is an NPC here: that parent dies (a real death, with a body).  Then watch: grief, who keeps them, their talk.",
     [m("pf_awl_k = 0"),
      {"u_run_npc_eocs": [{"id": "PF_AWL_loss_kid", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, m("pf_awl_k == 0"), m("has_var(u_pf_mom)")]},
                           "effect": [{"copy_var": {"u_val": "pf_mom"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
                                      {"if": m("pf_find_ok == 0"), "then": [{"copy_var": {"u_val": "pf_dad"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"}]},
                                      {"if": m("pf_find_ok == 1"), "then": [m("pf_awl_k = 1"), name_into("pf_awl_kid"), {"run_eocs": "PF_AWL_loss_die", "alpha_talker": g("pf_find_who")}]}]}],
       "local": True, "npc_range": 30},
      {"if": m("pf_awl_k == 0"), "then": [stat_say("No child nearby with a mother or father here.")], "else": [stat_say("<global_val:pf_awl_kid> has lost a parent.")]}]),
    ("PF_AWL_kid_grief", "Loss: a grieving child's day line now", "Every child nearby who is mourning a parent says their grief line (a kids' day step, forced).",
     [m("pf_kl = 0"), {"u_run_npc_eocs": [{"id": "PF_AWL_kg", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, m("has_var(u_pf_lost_t)")]}, "effect": [name_into("pf_say_a"), {"run_eocs": "PF_FAM_kid_grief"}]}],
                       "local": True, "npc_range": 30}]),
    ("PF_AWL_kid_heal", "Loss: a grieving child's mourning ends now", "Ends the mourning of every grieving child nearby and runs the day it lifts (a first laugh, a bond to whoever stayed).",
     [m("pf_kl = 0"), {"u_run_npc_eocs": [{"id": "PF_AWL_kh", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, m("has_var(u_pf_lost_t)")]},
                                           "effect": [m("u_pf_mourn_until = time('now')"), name_into("pf_say_a"), {"run_eocs": "PF_FAM_kid_heal"}]}], "local": True, "npc_range": 30}]),
    ("PF_AWL_tense", "Evening: the tense evening now", "The evening the dead won't leave: a line and shared danger with the grown-ups near you (ignores the clock and the threat).",
     [m("pf_eve_hit_t = 0"), m("pf_eve_day = " + TODAY), {"run_eocs": "PF_FIRE_tense"},
      {"if": m("pf_ft_n == 0"), "then": [stat_say("Nobody grown-up near you (15 tiles).")]}]),
]
lab = [eoc(i, e, d) for i, n, d, e in ROWS]
lab.append(eoc("PF_AWL_loss_die", ["u_die"], "Lab: u = the parent, dies now (a normal death)."))
lab.append(eoc("PF_AWL_road_i", [
    {"set_string_var": "pf_slot_<global_val:pf_rdl_i>", "target_var": ctx("ref"), "parse_tags": True},
    {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [
        by_uid([{"id": "PF_AWL_road_try", "condition": {"and": [m("value_or(u_pf_settled, 0) == 0"), m("value_or(u_pf_online, 0) == 0"), m("value_or(u_pf_visiting, 0) == 0")]},
                 "effect": [m("pf_rdl_done = 1"), name_into("pf_rdl_name"), {"run_eocs": "PF_ROAD_trouble"}]}], {"var_val": "ref"})]},
    m("pf_rdl_i += 1"),
], "Lab: roster slot i, if its band is off-screen and on the move."))
lab.append(eoc("PF_AWL_open", [{"run_eoc_selector": [i for i, n, d, e in ROWS], "names": [n for i, n, d, e in ROWS], "descriptions": [d for i, n, d, e in ROWS],
                                "keys": [string.ascii_lowercase[k] for k in range(len(ROWS))], "title": "Open threads lab (v0.7)", "allow_cancel": True}]))
files["lab_away.json"] = lab

for fname, data in files.items():
    json.dump(data, open(os.path.join(OUT, fname), "w", encoding="utf-8", newline="\n"), indent=2)
print("away written:", {k: len(v) for k, v in files.items()})
