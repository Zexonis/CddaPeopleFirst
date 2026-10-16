"""Generates mods/PeopleFirst/life/*.json: the v0.1 thin pass of every system (concept §12.11 step 2).

Every system here only (a) reads views through PF_VIEW_read and (b) reports moments through PF_MK_<kind>.
None of them touches another system or a bond directly.  NPCs pick who acts from their *own* views (autonomy).

Usage:  python tools/gen_life.py mods/PeopleFirst/life
"""
import json, os, sys

OUT = sys.argv[1]
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
HOME = "value_or(pf_eve_home, 0) == 1"
def hsay(text, home, t="info"):
    """A line that changes when tonight's evening is indoors at home (v0.4) instead of at a fire."""
    return {"if": {"math": [HOME]}, "then": [say(home, t)], "else": [say(text, t)]}
def name_into(gvar, tag="<u_name>"): return {"set_string_var": tag, "target_var": g(gvar), "parse_tags": True}
def read_view_of_avatar(): return [{"run_eocs": "PF_ID_ensure"}, {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"}]
def cooldown_ok_c(var, dur):
    return {"or": [m(f"time_since({var}) < 0"), m(f"time_since({var}) > time('{dur}')")]}

THREAT_SCAN = {"run_eocs": "PF_THREAT_scan", "alpha_talker": "avatar"}

files = {}

# ============================================================ THREAT  (is it safe to be social?  walls matter: a zombie stuck behind one isn't a threat)
files["threat.json"] = [
    eoc("PF_THREAT_scan", [
        m("pf_threat = u_monsters_nearby('radius': 3) + u_characters_nearby('radius': 20, 'attitude': 'hostile')"),
        {"u_run_monster_eocs": ["PF_THREAT_seen"], "monster_range": 20, "monster_must_see": True},
    ], "u = avatar.  pf_threat = hostile monsters you can see within 20 tiles + any hostile monster within 3 (seen or not, it's at the door) + hostile NPCs within 20.  0 means calm.  (characters_nearby ignores monsters; monsters_nearby ignores walls, so on its own it would cancel every evening next to a zombie pit.)"),
    eoc("PF_THREAT_seen", [m("pf_threat += 1")],
        "u = a monster you can see.  It counts itself in monsters_nearby at radius 0 only if it is hostile to you.",
        condition=m("u_monsters_nearby('radius': 0) > 0")),
]

# ============================================================ CARE  (story 1: hot tea when you come back soaked and freezing)
PARTS = ["torso", "head", "eyes", "mouth", "arm_l", "arm_r", "hand_l", "hand_r", "leg_l", "leg_r", "foot_l", "foot_r"]
def any_part(*effects):
    """u has one of these effects on any body part.  A bare u_has_effect checks only the whole-body slot, so a bite on the leg
    reads false (full run: nobody tended a bitten leg; PF_DBG_tend said hurt 0)."""
    return {"or": [{"u_has_effect": e, "bodypart": bp} for e in effects for bp in PARTS] + [{"u_has_effect": e} for e in effects]}
HP_PARTS = ["torso", "head", "arm_l", "arm_r", "leg_l", "leg_r"]
# full run (day 65): arms and legs chewed on a city run, no bite effect, torso fine: nobody tended.  Any main part at 80% or less.
HURT = {"or": [m(f"u_hp('{p}') <= u_hp_max('{p}') * 0.8") for p in HP_PARTS] + [any_part("bleed", "bite")]}
files["care.json"] = [
    eoc("PF_CARE_on_effect", [{"run_eocs": "PF_CARE_check", "time_in_future": "3 minutes"}],
        "Bottom-up signal: the avatar gains wet or cold.  A few minutes later, someone who cares may notice.",
        condition={"and": ["u_is_avatar", {"compare_string": [ctx("effect"), "wet", "cold"]}]},
        eoc_type="EVENT", required_event="character_gains_effect"),
    eoc("PF_CARE_check", [
        m("pf_care_best = -1"),
        {"u_run_npc_eocs": ["PF_CARE_candidate"], "local": True, "npc_range": 20},
        {"if": m("pf_care_best >= 0"), "then": [
            m("pf_care_last = time('now')"),
            {"u_location_variable": g("pf_care_av")},
            {"if": {"u_has_effect": "wet"}, "then": [{"set_string_var": "wet", "target_var": g("pf_care_why")}],
             "else": [{"set_string_var": "cold", "target_var": g("pf_care_why")}]},
            {"run_eocs": "PF_CARE_give", "alpha_talker": g("pf_care_who")}]},
    ], "u = avatar.  Every nearby NPC weighs in from its own view of you; the one who cares most acts.  At most once every 2 hours.",
        condition={"and": [{"or": [{"u_has_effect": "wet"}, {"u_has_effect": "cold"}]}, cooldown_ok_c("pf_care_last", "2 h")]}),
    eoc("PF_CARE_candidate", read_view_of_avatar() + [
        m("_score = pf_read_w + (pf_read_t / 2)"),
        {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("_score += 15")]},
        {"if": {"u_has_trait": "PF_T_SOCIABLE"}, "then": [m("_score += 3")]},
        {"if": {"and": [m("_score >= 10"), m("_score > pf_care_best")]},
         "then": [m("pf_care_best = _score"), {"u_set_talker": g("pf_care_who")}]},
    ], "u = a nearby NPC.  Will they help?  Warmth, half of trust, +15 if a mother hen.  Needs 10: strangers don't, unless they're the mothering kind."),
    eoc("PF_WOUND_tick", [
        THREAT_SCAN,
        {"if": m("pf_threat == 0"), "then": [
            m("pf_care_best = -1"),
            {"u_run_npc_eocs": ["PF_CARE_candidate"], "local": True, "npc_range": 20},
            {"if": m("pf_care_best >= 0"), "then": [
                m("pf_wound_last = time('now')"),
                {"u_location_variable": g("pf_care_av")},
                {"run_eocs": "PF_WOUND_tend", "alpha_talker": g("pf_care_who")}]}]},
    ], "Every 10 minutes: if you're hurt (torso at 80% or less, bleeding, or bitten) and it's calm (PF_THREAT_scan), the person who cares most comes and tends your wounds (once an hour at most).",
        condition={"and": [HURT, cooldown_ok_c("pf_wound_last", "1 h")]},
        recurrence="10 minutes", **{"global": True}),
    eoc("PF_WOUND_tend", [
        {"copy_var": g("pf_care_av"), "target_var": {"u_val": "pf_walk_to"}},
        {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": 1},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
        name_into("pf_say_a"),
        {"run_eocs": "PF_WOUND_heal", "alpha_talker": "avatar"},
        {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "wounds"}},
        m("pf_m_str_in = 70"),
        {"run_eocs": "PF_MK_care_given", "beta_talker": "avatar"},
    ], "u = the carer.  Cleans and binds your wounds: stops bleeding, cleans bites, and a little healing.  Strength 70, so you both remember it."),
    eoc("PF_DBG_tend", [
        m("pf_dbg_a = 0"), {"if": HURT, "then": [m("pf_dbg_a = 1")]},
        m("pf_dbg_b = time_since(pf_wound_last, 'unit': 'minutes')"),
        THREAT_SCAN, m("pf_dbg_c = pf_threat"),
        m("pf_dbg_d = u_monsters_nearby('radius': 3)"), m("pf_dbg_e = u_characters_nearby('radius': 20, 'attitude': 'hostile')"),
        m("pf_care_best = -1"), {"u_run_npc_eocs": ["PF_CARE_candidate"], "local": True, "npc_range": 20},
        say("[debug] tending: hurt <global_val:pf_dbg_a>, minutes since last <global_val:pf_dbg_b>, threat <global_val:pf_dbg_c> (within 3: <global_val:pf_dbg_d>, hostile people: <global_val:pf_dbg_e>), best carer score <global_val:pf_care_best>."),
    ], "Debug only (run from the debug menu, u = avatar): why nobody tends your wounds.  Reports each gate of PF_WOUND_tick."),
    eoc("PF_WOUND_heal", [
        {"u_lose_effect": ["bleed", "bite"], "target_part": "ALL"},
        m("u_hp('torso') = min(u_hp('torso') + 6, u_hp_max('torso'))"),
    ] + [m(f"u_hp('{p}') = min(u_hp('{p}') + 4, u_hp_max('{p}'))") for p in HP_PARTS if p != "torso"],
        "u = avatar.  Cleaned and bound: bleeding and bites gone, a little back on every main part."),
    eoc("PF_CARE_give", [
        {"copy_var": g("pf_care_av"), "target_var": {"u_val": "pf_walk_to"}},
        {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": 1},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
        name_into("pf_say_a"),
        {"run_eocs": "PF_GIVE_tea", "alpha_talker": "avatar"},
        {"if": {"u_has_trait": "PF_T_LONER"},
         "then": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "care_loner"}}],
         "else": [{"if": {"compare_string": [g("pf_care_why"), "wet"]},
                   "then": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "care"}}],
                   "else": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "care_cold"}}]}]},
        {"run_eocs": "PF_MK_care_given", "beta_talker": "avatar"},
    ], "u = the carer.  Comes over, leaves hot tea at your feet, and the moment is reported (care_given: carer -> you)."),
]

# ============================================================ FIND  (re-resolve a person later: stored character ids go stale)
files["find.json"] = [
    eoc("PF_FIND_by_uid", [
        m("pf_find_ok = 0"),
        {"u_run_npc_eocs": ["PF_FIND_check"], "local": True, "npc_range": 60},
    ], "Looks among loaded NPCs for the one whose pf_uid equals pf_find_uid.  Sets pf_find_ok and the talker pf_find_who.  Use this whenever time has passed since you stored someone: run_eocs on a stale character id crashes the game."),
    eoc("PF_FIND_check", [m("pf_find_ok = 1"), {"u_set_talker": g("pf_find_who")}],
        condition={"and": [m("pf_find_ok == 0"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_find_uid")]}]}),
]

# ============================================================ NIGHT WATCH  (story 4: someone stays up for you)
files["watch.json"] = [
    eoc("PF_WATCH_on_sleep", [
        {"if": {"and": [m("value_or(pf_wt_on, 0) == 1"), m("value_or(pf_wt_night, -1) == floor((time('now') - time('12 h')) / time('1 d'))")]},
         "then": [{"run_eocs": "PF_SAY_town", "alpha_talker": "avatar", "variables": {"line": "watch_sleep"}}],
         "else": [
        # full run: a night where you never got to sleep left the watch open; you woke far away the next night to
        # "Whoever had the watch is gone."  Each sleep starts with no watch.
        m("pf_watch_active = 0"), m("pf_watch_band = 0"),
        m("pf_watch_best = -1"),
        {"if": HURT, "then": [m("pf_watch_hurt = 1")], "else": [m("pf_watch_hurt = 0")]},
        {"u_location_variable": g("pf_watch_av")},
        {"u_run_npc_eocs": ["PF_WATCH_candidate"], "local": True, "npc_range": 20},
        {"if": m("pf_watch_best >= 0"), "then": [
            m("pf_watch_active = 1"),
            {"run_eocs": "PF_WATCH_take", "alpha_talker": g("pf_watch_who")}]}]},
        # full run day 78: woken four times in one night by "Something is making noise." (the household fighting the dead
        # outside); with someone on watch you sleep through the small noises.  Gunfire close by still wakes you; so does the
        # Horn for anything in sight within 6 tiles, and being hit.
        {"if": {"or": [m("value_or(pf_watch_active, 0) == 1"),
                       {"and": [m("value_or(pf_wt_on, 0) == 1"), m("value_or(pf_wt_night, -1) == floor((time('now') - time('12 h')) / time('1 d'))")]}]},
         "then": [{"u_add_effect": "PF_sleep_easy", "duration": "12 h"}]},
    ], "Signal: the avatar falls asleep.  The person who trusts you most takes the watch; whoever watched last time steps back (a rota).  When the town watch is up (v0.5 Town pass 3), it has the watch instead.",
        condition="u_is_avatar", eoc_type="EVENT", required_event="character_falls_asleep"),
    eoc("PF_WATCH_candidate", read_view_of_avatar() + [
        m("_score = pf_read_t + 5"),
        {"if": {"u_has_trait": "PF_Q_LOYAL"}, "then": [m("_score += 15")]},
        {"if": {"compare_string": [{"u_val": "pf_uid"}, g("pf_watch_last")]}, "then": [m("_score -= 20")]},
        {"run_eocs": "PF_FAM_watch_bonus"}, m("_score += pf_fm_watch_add"),
        {"if": m("value_or(u_pf_role, 0) == 2"), "then": [m("_score += 15")]},
        {"if": {"u_has_trait": "PF_CHILD"}, "then": [m("_score = -1000")]},
        {"if": {"and": [m("_score >= 0"), m("_score > pf_watch_best")]},
         "then": [m("pf_watch_best = _score"), {"u_set_talker": g("pf_watch_who")}]},
    ], "u = a nearby NPC.  Trust, +15 if loyal, -20 if they watched last time."),
    eoc("PF_WATCH_take", [
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_watch_uid")}, m("pf_watch_t = time('now')"),
        # full run day 151: Golly (a band leader) took the watch at Dante's side, her band set off at 06:00, and he woke to
        # "Whoever had the watch is gone."  A band whose member is on watch for you holds camp until you wake (alife.json).
        m("pf_watch_band = (value_or(u_pf_resident, 0) == 0) * value_or(u_pf_band, 0)"),
        name_into("pf_watch_name"),
        {"copy_var": g("pf_watch_av"), "target_var": {"u_val": "pf_walk_to"}},
        {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": 2},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
        name_into("pf_say_a"),
        {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "watch_take"}},
    ]),
    eoc("PF_WATCH_on_wake", [
        m("pf_watch_active = 0"),
        {"u_location_variable": g("pf_watch_av")},
        {"copy_var": g("pf_watch_uid"), "target_var": g("pf_find_uid")},
        {"run_eocs": "PF_FIND_by_uid"},
        {"if": m("pf_find_ok == 1"),
         "then": [{"run_eocs": "PF_WATCH_done", "alpha_talker": g("pf_find_who")}],
         "else": [{"if": m("value_or(pf_watch_band, 0) > 0"),
                   "then": [say("<global_val:pf_watch_name> kept watch until first light, then went on with their people.")],
                   "else": [say("Whoever had the watch is gone.", "bad")]}]},
        m("pf_watch_band = 0"),
    ], condition={"and": ["u_is_avatar", m("value_or(pf_watch_active, 0) == 1"), m("time('now') - value_or(pf_watch_t, 0) <= time('16 h')")]},
        eoc_type="EVENT", required_event="character_wakes_up"),
    {"type": "effect_type", "id": "PF_sleep_easy", "name": ["Sleeping easy"],
     "desc": ["Someone has the watch.  You sleep through the small noises."], "rating": "good", "max_duration": "12 h",
     "enchantments": [{"values": [{"value": "HEARING_MULT", "multiply": -0.6}]}]},
    eoc("PF_SLEEP_easy_end", [{"u_lose_effect": "PF_sleep_easy"}], "Awake again: your hearing is your own.",
        condition={"and": ["u_is_avatar", {"u_has_effect": "PF_sleep_easy"}]}, eoc_type="EVENT", required_event="character_wakes_up"),
    eoc("PF_WATCH_stale", [m("pf_watch_active = 0"), m("pf_watch_band = 0")],
        "A watch older than a night (you never slept) closes quietly.",
        condition={"and": ["u_is_avatar", m("value_or(pf_watch_active, 0) == 1"), m("time('now') - value_or(pf_watch_t, 0) > time('16 h')")]},
        eoc_type="EVENT", required_event="character_wakes_up"),
    eoc("PF_WATCH_done", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_watch_av) <= 20"), "then": [
            name_into("pf_say_a"),
            {"if": m("pf_watch_hurt == 1"),
             "then": [{"run_eocs": "PF_WOUND_heal", "alpha_talker": "avatar"},
                      {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "watch_bandaged"}},
                      m("pf_m_str_in = 80"), {"run_eocs": "PF_MK_care_given", "beta_talker": "avatar"},
                      m("pf_wound_last = time('now')")],
             "else": [{"if": m("time('now') - value_or(pf_watch_t, 0) >= time('3 h')"),
                       "then": [{"if": m("(floor((value_or(pf_watch_t, 0) % time('1 d')) / time('1 h')) >= 6) * (floor((value_or(pf_watch_t, 0) % time('1 d')) / time('1 h')) < 18)"),
                                 "then": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "watch_done_day"}}],
                                 "else": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "watch_done"}}]}],
                       "else": [{"if": m("time('now') - value_or(pf_watch_t, 0) >= time('30 m')"),
                                 "then": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "watch_short"}}]}]}]},
            {"if": m("time('now') - value_or(pf_watch_t, 0) >= time('3 h')"), "then": [{"run_eocs": "PF_MK_watch_covered", "beta_talker": "avatar"}]},
            {"copy_var": g("pf_watch_uid"), "target_var": g("pf_watch_last")}]},
    ], "u = the watcher when you wake.  If they stayed close, a real night (3 hours or more) counts: watch_covered (watcher to you) and \"kept watch through the night\".  A nap gets a smaller line, or none under 30 minutes (playtest 3: \"kept watch through the night\" after a one-minute doze at 20:35)."),
]

# ============================================================ FIRE EVENING  (story 3) + RECALL (story 2) + bickering (friction)
SEATS = [(-2, 0), (2, 0), (0, 2), (-2, 2), (2, 2), (0, -2)]
seat_x = " + ".join(f"(pf_fire_n == {i}) * {x}" for i, (x, y) in enumerate(SEATS))
seat_y = " + ".join(f"(pf_fire_n == {i}) * {y}" for i, (x, y) in enumerate(SEATS))
files["fire.json"] = [
    eoc("PF_FIRE_tick", [{"run_eocs": "PF_FIRE_look"}],
        "Every 10 minutes from 19:00 to midnight, while you're awake (playtest 3: the evening went on, and spoke to you, while you slept), until tonight's evening has happened.  The evening is a state machine (pf_eve_state): 0 nothing yet, 1 seated, 2 broken up by trouble, 3 done.",
        condition={"and": [m("time_since('midnight', 'unit': 'hours') >= 19"),
                           m("value_or(pf_eve_done_day, -1) != floor(time('now') / time('1 d'))"),
                           {"not": {"u_has_effect": "sleep"}}]},
        recurrence="10 minutes", **{"global": True}),
    eoc("PF_FIRE_look", [
        {"if": m("value_or(pf_eve_day, -1) != floor(time('now') / time('1 d'))"),
         "then": [m("pf_eve_day = floor(time('now') / time('1 d'))"), m("pf_eve_state = 0"), m("pf_eve_fought = 0")]},
        {"u_location_variable": g("pf_fire_loc"), "field": "fd_fire", "target_max_radius": 15,
         "true_eocs": [{"id": "PF_FIRE_found", "effect": [m("pf_eve_home = 0"), {"run_eocs": "PF_FIRE_step"}]}],
         "false_eocs": [{"id": "PF_FIRE_nofire", "effect": [
             {"if": m("value_or(pf_eve_state, 0) == 1"), "then": [{"run_eocs": "PF_FIRE_step"}],
              "else": [{"run_eocs": "PF_HOME_hearth"},
                       # Kinfold day 136: Dante spent the evening at Janey Hammond's camp and nothing happened (no fire, no
                       # furniture, 34 tiles from home).  A band leader within 8 tiles: the evening is at their camp.
                       {"if": m("value_or(pf_eve_state, 0) == 0"), "then": [{"run_eocs": "PF_FIRE_camp"}]}]}]}]},
    ], "u = avatar.  New day: reset the evening.  Then, if a fire burns within 15 tiles, advance the evening.  Once people are seated, the evening goes on around the embers even if the fire has burned down (the natural playtest had them sitting by a dead fire all night)."),
    eoc("PF_FIRE_camp", [
        m("pf_camp_found = 0"),
        {"u_run_npc_eocs": [{"id": "PF_FIRE_camp_lead", "condition": {"and": [m("value_or(u_pf_is_leader, -1) == 1"), m("value_or(u_pf_resident, 0) == 0")]},
                             "effect": [{"if": m("pf_camp_found == 0"), "then": [m("pf_camp_found = 1"), {"u_location_variable": g("pf_fire_loc")},
                                                                                       name_into("pf_camp_name")]}]}],
         "local": True, "npc_range": 8},
        {"if": m("pf_camp_found == 1"), "then": [{"run_eocs": "PF_FIRE_camp_fire"}, m("pf_eve_home = 0"), {"run_eocs": "PF_FIRE_step"}]},
    ], "u = avatar, an evening with no fire or home furniture near: if a band's leader is within 8 tiles, you spend the evening at their camp (seated around them)."),
    # full run day 139: "people drift toward the fire" and "sits close to the fire" at a camp with no fire.  A band out in
    # the open lights one: their old fire ring if there is one near, else a new ring beside the leader, on diggable ground
    # (never water), the grass around it cleared, and a log on it.
    eoc("PF_FIRE_camp_fire", [
        m("pf_camp_ok = 0"), m("pf_camp_new = 0"),
        {"u_location_variable": g("pf_camp_ring"), "furniture": "f_firering", "target_max_radius": 10,
         "true_eocs": [{"id": "PF_FIRE_camp_ring", "effect": [m("pf_camp_ok = 2"),
             {"if": m("characters_nearby('radius': 0, 'location': pf_camp_ring) == 0"),
              "then": [{"copy_var": g("pf_camp_ring"), "target_var": g("pf_fire_loc")}, m("pf_camp_ok = 1")]}]}]}] + [
        {"if": m("pf_camp_ok == 0"), "then": [
            {"copy_var": g("pf_fire_loc"), "target_var": g("pf_camp_try")},
            {"location_variable_adjust": g("pf_camp_try"), "x_adjust": dx, "y_adjust": dy},
            # Kinfold day 140: the ring went down under Dante (two tiles from the leader) and set him on fire; he broke a leg in
            # it before the game was killed.  Nobody may stand on the spot or next to it.
            {"if": {"and": [{"map_terrain_with_flag": "DIGGABLE", "loc": g("pf_camp_try")}, {"map_furniture_id": "f_null", "loc": g("pf_camp_try")},
                            m("characters_nearby('radius': 1, 'location': pf_camp_try) == 0")]},
             "then": [{"u_transform_radius": 1, "ter_furn_transform": "PF_LL_clear_grass", "target_var": g("pf_camp_try")},
                      {"u_transform_radius": 0, "ter_furn_transform": "PF_LL_firering", "target_var": g("pf_camp_try")},
                      {"copy_var": g("pf_camp_try"), "target_var": g("pf_fire_loc")}, m("pf_camp_ok = 1"), m("pf_camp_new = 1")]}]}
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (-2, -2), (2, -2), (-2, 2), (3, 0), (-3, 0), (0, 3), (0, -3))] + [
        {"if": m("pf_camp_ok == 1"), "then": [
            {"map_spawn_item": "log", "loc": g("pf_fire_loc")},
            {"u_set_field": "fd_fire", "radius": 0, "intensity": 1, "age": "0 seconds", "hit_player": False, "target_var": g("pf_fire_loc")},
            {"if": m("pf_camp_new == 1"), "then": [say("<global_val:pf_camp_name> scrapes a ring in the dirt, sets stones around it and gets a fire going.")],
             "else": [say("<global_val:pf_camp_name> gets the fire going again in the old ring.")]}]},
    ], "u = avatar.  pf_fire_loc = the band leader.  Lights the camp's fire and moves pf_fire_loc to it."),
    eoc("PF_FIRE_step", [
        THREAT_SCAN,
        {"if": m("pf_threat > 0"),
         "then": [{"if": m("pf_eve_state == 1"), "then": [{"run_eocs": "PF_FIRE_scatter"}],
                   # v0.7 (concept 15.4): the dead won't leave the door; by 21:00, with nobody hit for half an hour, the evening happens anyway, low
                   "else": [{"if": m("(time_since('midnight', 'unit': 'hours') >= 21) * (pf_eve_state != 3) * (time('now') - value_or(pf_eve_hit_t, 0) >= time('30 m'))"),
                             "then": [{"run_eocs": "PF_FIRE_tense"}]}]}],
         "else": [{"if": {"and": [m("pf_eve_state != 1"), m("pf_eve_state < 3")]},
                   "then": [{"run_eocs": "PF_FIRE_gather"}],
                   "else": [{"if": {"and": [m("pf_eve_state == 1"), m("time_since(pf_eve_seat_t) >= time('20 m')")]},
                             # full run day 150: Golly's band was seated and walked on; the evening ran with nobody at the fire and
                             # was spent.  Nobody within 10 tiles of the fire: seat them again instead.
                             "then": [m("pf_fc_n = 0"),
                                      {"u_run_npc_eocs": [{"id": "PF_FIRE_count_one", "condition": m("value_or(u_pf_fire_seated, -1) == pf_eve_day"),
                                                           "effect": [{"u_location_variable": {"u_val": "pf_pos"}},
                                                                      {"if": m("distance(u_pf_pos, pf_fire_loc) <= 10"), "then": [m("pf_fc_n += 1")]}]}],
                                       "local": True, "npc_range": 40},
                                      {"if": m("pf_fc_n == 0"), "then": [m("pf_eve_state = 0")],
                                       "else": [{"run_eocs": "PF_FIRE_beat"}, m("pf_eve_state = 3"), m("pf_eve_done_day = pf_eve_day")]}]}]}]},
    ], "u = avatar.  Trouble: if people are seated, they scatter (fights matter more than seats).  Calm: people sit down (or come back after a fight), and 20-30 minutes after sitting down the evening happens, if anyone is actually at the fire (else they're seated again).  So danger interrupts the evening instead of cancelling it, and a zombie stuck behind a wall doesn't stop it."),
    eoc("PF_FIRE_gather", [
        m("pf_fire_n = 0"), m("pf_fire_recalled = 0"),
        m("pf_rc_kids = 0"), {"u_run_npc_eocs": ["PF_FIRE_join"], "local": True, "npc_range": 30},
        m("pf_rc_kids = 1"), {"u_run_npc_eocs": ["PF_FIRE_join"], "local": True, "npc_range": 30},
        {"if": m("pf_fire_n > 0"), "then": [
            {"if": m("pf_eve_state == 2"),
             # full run day 77: scattered and back twice in an hour; each line once an evening
             "then": [{"if": m("value_or(pf_eve_back_day, -1) != pf_eve_day"), "then": [
                 m("pf_eve_back_day = pf_eve_day"),
                 hsay("With the dead quiet again, people drift back to the fire.", "With the dead quiet again, people drift back inside.")]}],
             "else": [{"if": m("value_or(pf_eve_drift_day, -1) != pf_eve_day"), "then": [
                 m("pf_eve_drift_day = pf_eve_day"),
                 hsay("As evening settles, people drift toward the fire.", "As evening settles, people drift in and pull up chairs.")]}]},
            m("pf_eve_state = 1"), m("pf_eve_seat_t = time('now')")]},
    ], "u = avatar.  Up to 6 nearby people walk to seats around the fire (loners sit farther out)."),
    eoc("PF_FIRE_tense", [
        m("pf_ft_n = 0"),
        {"u_run_npc_eocs": [{"id": "PF_FIRE_tense_one", "condition": {"and": [m("has_var(u_pf_uid)"), {"not": {"u_has_trait": "PF_CHILD"}}, {"not": {"u_has_effect": "sleep"}}]},
                             "effect": [m("pf_ft_n += 1"), m("pf_m_str_in = 35"), {"run_eocs": "PF_MK_shared_danger", "beta_talker": "avatar"}]}], "local": True, "npc_range": 15},
        {"if": m("pf_ft_n > 0"), "then": [
            m("_t = rand(2)"), {"if": m("_t == value_or(pf_ft_last, -1)"), "then": [m("_t = (_t + 1) % 3")]}, m("pf_ft_last = _t"),
            {"if": m("value_or(pf_set_chatter, 1) == 1"), "then": [{"if": m("_t == 0"), "then": [hsay('Nobody sits down properly tonight.  People eat standing up, backs to the fire, talking in whispers, and somebody tells a joke anyway.', 'Nobody sits down properly tonight.  People eat standing up, away from the windows, talking in whispers, and somebody tells a joke anyway.', "info")]}, {"if": m("_t == 1"), "then": [hsay("The fire is kept low, and nobody strays out of its light.  It's not much of an evening.  It's still an evening.", "The lamp is kept low and the door stays barred.  It's not much of an evening.  It's still an evening.", "info")]}, {"if": m("_t == 2"), "then": [hsay("Out there the dead keep at it.  Here, someone hums, someone else picks it up, and for a while that's louder.", "Out there the dead keep at it.  In here, someone hums, someone else picks it up, and for a while that's louder.", "info")]}]},
            m("pf_eve_state = 3"), m("pf_eve_done_day = pf_eve_day"), m("pf_eve_tense_total = value_or(pf_eve_tense_total, 0) + 1")]},
    ], "u = avatar.  The evening the dead won't leave (concept 15.4): no seats; a line; shared danger (35) between you and the grown-ups near you; it counts as tonight's evening."),
    eoc("PF_FIRE_hit_mark", [m("pf_eve_hit_t = time('now')")],
        "Someone of ours (or you) was hit: the tense evening waits half an hour after the last blow.",
        condition={"and": ["has_beta", {"or": ["u_is_avatar", m("has_var(u_pf_uid)")]}, m("time_since('midnight', 'unit': 'hours') >= 19")]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    eoc("PF_FIRE_scatter", [
        m("pf_eve_state = 2"), m("pf_eve_fought = 1"),
        {"u_run_npc_eocs": ["PF_FIRE_unseat"], "local": True, "npc_range": 40},
        {"if": m("value_or(pf_eve_sc_day, -1) != value_or(pf_eve_day, -2)"), "then": [
            m("pf_eve_sc_day = value_or(pf_eve_day, -2)"),
            hsay("Trouble.  The fire is forgotten as people reach for their weapons.", "Trouble.  Chairs scrape back as people reach for their weapons.", "bad")]},
    ], "u = avatar.  Cancels everyone's walk order to their seat so they fight instead.  The evening resumes once it's calm (state 2)."),
    eoc("PF_FIRE_unseat", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"u_set_guard_pos": {"u_val": "pf_pos"}},
    ], "u = someone who was walking to a seat.  A walk order to where they already stand is dropped at once.",
        condition=m("value_or(u_pf_fire_seated, -1) == pf_eve_day")),
    eoc("PF_FIRE_hit", [{"run_eocs": "PF_FIRE_scatter", "alpha_talker": "avatar"}],
        "Fast path: someone is hit by an attacker while people are walking to their seats.  Don't wait for the 10-minute tick.",
        condition={"and": [m("value_or(pf_eve_state, 0) == 1"), "has_beta", {"or": ["u_is_avatar", "u_is_npc"]}]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    eoc("PF_FIRE_beat", [
        {"run_eocs": "PF_ID_ensure"},
        m("pf_beat_id = value_or(pf_beat_id, 0) + 1"),
        m("pf_fire_n = 0"), m("pf_fire_recalled = 0"),
        # Kinfold day 148: nine at home, and the roll call (first 6 in load order) was five children and Mitzi every night;
        # Janey and Beau, new that week, never had an evening.  Grown-ups first, then children.
        m("pf_rc_kids = 0"), {"u_run_npc_eocs": ["PF_FIRE_rollcall"], "local": True, "npc_range": 40},
        m("pf_rc_kids = 1"), {"u_run_npc_eocs": ["PF_FIRE_rollcall"], "local": True, "npc_range": 40},
        {"u_location_variable": g("pf_fire_av")},
        m("pf_fire_service = 0"), m("pf_fire_wedding = 0"),
        {"run_eocs": "PF_HEART_service"},
        {"run_eocs": "PF_HEART_wedding_try"},
        m("pf_fire_av_here = distance(pf_fire_av, pf_fire_loc) <= 8"),
        {"if": {"and": [m("pf_fire_n > 0"), m("value_or(pf_eve_fought, 0) == 1")]},
         "then": [hsay("Nobody talks much about the fight.  A bottle goes around instead, and the fire feels warmer for it.", "Nobody talks much about the fight.  A bottle goes around instead, and the room feels warmer for it.", "good")]},
        {"if": {"and": [m("pf_fire_n > 0"), m("pf_fire_av_here"), m("value_or(pf_eve_fought, 0) == 0"), m("pf_fire_service == 0")]}, "then": [{"run_eocs": "PF_RK_retell"}]},
        # full run day 94: the dead came by at dusk (they do most evenings at Kinfold), and a fought evening skipped the harvest
        # feast for good; the feast happens anyway, once it's quiet again (a fight only made it later)
        {"if": {"and": [m("pf_fire_n > 0"), m("pf_fire_av_here")]}, "then": [{"run_eocs": "PF_TOWN_feast"}]},
        m("pf_eve_fought = 0"),
        m("pf_fi = 0"),
        {"run_eocs": "PF_FIRE_pairs_from_i", "condition": m("pf_fi < pf_fire_n"), "iterations": 10},
        m("pf_fi = 0"), m("pf_fire_acts = (pf_fire_service + pf_fire_wedding > 0) * 3"),
        m("pf_fire_off = pf_fire_n > 1 ? rand(pf_fire_n - 1) : 0"),  # the three activities start somewhere new each night
        {"run_eocs": "PF_FIRE_activity_i", "condition": {"and": [m("pf_fi < pf_fire_n"), m("pf_fire_acts < 3")]}, "iterations": 10},
        m("pf_fi = 0"), m("pf_rom_done = 0"),
        {"if": {"and": [m("value_or(pf_set_romance, 2) >= 1"), m("pf_fire_service == 0")]}, "then": [
            {"run_eocs": "PF_HEART_fire"},
            m("pf_fi = 0"),
            {"run_eocs": "PF_ROM_fire_i", "condition": {"and": [m("pf_fi < pf_fire_n"), m("pf_rom_done < 2")]}, "iterations": 10}]},
        {"run_eocs": "PF_HEART_anniv"},
        {"if": m(HOME), "then": [{"run_eocs": "PF_HOME_beat_extra"}]},
        m("pf_fi = 0"), m("pf_fire_mourned = 0"),
        {"run_eocs": "PF_GRIEF_recall_i", "condition": {"and": [m("pf_fi < pf_fire_n"), m("pf_fire_mourned == 0")]}, "iterations": 10},
        {"if": m("pf_fire_av_here"), "then": [
            m("pf_fi = 0"),
            {"run_eocs": "PF_FIRE_with_avatar_i", "condition": m("pf_fi < pf_fire_n"), "iterations": 10},
            m("pf_fi = 0"),
            {"run_eocs": "PF_FIRE_recall_i", "condition": {"and": [m("pf_fi < pf_fire_n"), m("pf_fire_recalled == 0")]}, "iterations": 10},
            {"run_eocs": "PF_HOME_rumor_try"}]},
    ], "u = avatar, 20-30 minutes after people sat down.  Everyone at the fire shares a fire_evening moment with everyone else (or bickers, if tension is high); up to three of them do something that fits their temperament; if you're at the fire you share the evening too, and someone may bring up a memory.  After a fight, it opens with the bottle line.  It starts with a fresh roll call (never trust a character id from earlier: running an EOC on someone who has since left the bubble crashes the game)."),
    eoc("PF_FIRE_rollcall", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_fire_loc) <= 10"), "then": [
            {"run_eocs": "PF_ID_ensure"},
            {"set_string_var": "pf_fire_u_<global_val:pf_fire_n>", "target_var": ctx("uref"), "parse_tags": True},
            {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "uref"}},
            {"set_string_var": "pf_fire_c_<global_val:pf_fire_n>", "target_var": ctx("ref"), "parse_tags": True},
            {"u_set_talker": {"var_val": "ref"}},
            m("pf_fire_n += 1")]},
    ], "u = a loaded NPC who sat down tonight.  Counts only if still within 10 tiles of the fire.",
        condition={"and": [m("pf_fire_n < 6"), m("value_or(u_pf_fire_seated, -1) == pf_eve_day"), {"not": {"u_has_effect": "PF_infant"}},
                           m("u_has_trait('PF_CHILD') == value_or(pf_rc_kids, 0)")]}),
    eoc("PF_FIRE_activity_i", [
        m("pf_fa_k = (pf_fi + value_or(pf_fire_off, 0)) % pf_fire_n"),
        {"set_string_var": "pf_fire_c_<global_val:pf_fa_k>", "target_var": ctx("ri"), "parse_tags": True},
        {"run_eocs": "PF_FIRE_activity_do", "alpha_talker": {"var_val": "ri"}},
        m("pf_fi += 1"),
    ]),
    eoc("PF_FIRE_activity_do", [
        name_into("pf_say_a"),
        {"set_string_var": "act_quiet", "target_var": g("pf_act")},
        {"if": {"u_has_trait": "PF_Q_PROUD"}, "then": [{"set_string_var": "act_proud", "target_var": g("pf_act")}]},
        {"if": {"u_has_trait": "PF_Q_GALLOWS"}, "then": [{"set_string_var": "act_joke", "target_var": g("pf_act")}]},
        {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [{"set_string_var": "act_cook", "target_var": g("pf_act")}]},
        {"if": {"u_has_trait": "PF_T_LONER"}, "then": [{"set_string_var": "act_whittle", "target_var": g("pf_act")}]},
        {"if": {"u_has_trait": "PF_T_SOCIABLE"}, "then": [{"set_string_var": "act_story", "target_var": g("pf_act")}]},
        # playtest 3: one act per temperament made every evening the same; one night in three people do something else
        {"if": {"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("rand(2) == 0")]}, "then": [
            m("_v = rand(4)")] + [{"if": m(f"_v == {i}"), "then": [{"set_string_var": a, "target_var": g("pf_act")}]}
                                 for i, a in enumerate(["act_quiet", "act_story", "act_joke", "act_whittle", "act_cook"])]},
        {"if": {"u_has_trait": "PF_CHILD"}, "then": [{"set_string_var": "act_child", "target_var": g("pf_act")}]},
        {"if": m("value_or(pf_keep_force, 0) == 1"), "then": [{"set_string_var": "act_whittle", "target_var": g("pf_act")}]},
        {"run_eocs": "PF_HOME_prop_act"},
        {"if": {"and": [m("time('now') < value_or(u_pf_mourn_until, 0)"), m("value_or(pf_prop_force, 0) == 0")]}, "then": [{"set_string_var": "act_mourn", "target_var": g("pf_act")}]},
        {"if": m("value_or(pf_set_chatter, 1) == 1"), "then": [{"run_eocs": "PF_SAY_act", "alpha_talker": "avatar"}]},
        {"if": {"compare_string": [g("pf_act"), "act_whittle"]}, "then": [{"run_eocs": "PF_KEEPSAKE_try"}]},
        m("pf_fire_acts += 1"),
    ], "u = someone at the fire.  Parallel play (story 3): what they do comes from who they are."),
    eoc("PF_KEEPSAKE_try", read_view_of_avatar() + [
        {"if": {"or": [m("value_or(pf_keep_force, 0) == 1"),
                       # full run days 166-167: Beau, then Emanuel, the same carving two nights running.  One keepsake
                       # for you every 5 days from the whole household, in a few words.
                       {"and": [m("pf_fire_av_here"), m("pf_read_w >= 15"), m("rand(2) == 0"),
                                m("time('now') - value_or(pf_keep_last_t, -999999) >= time('5 d')")]}]},
         "then": [m("pf_keep_force = 0"), m("pf_keep_last_t = time('now')"),
                  {"run_eocs": "PF_GIVE_keepsake", "alpha_talker": "avatar"},
                  m("_k = rand(2)"), {"if": m("_k == value_or(pf_keep_line_last, -1)"), "then": [m("_k = (_k + 1) % 3")]}, m("pf_keep_line_last = _k"),
                  {"if": m("_k == 0"), "then": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "keepsake"}}]},
                  {"if": m("_k == 1"), "then": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "keepsake_1"}}]},
                  {"if": m("_k == 2"), "then": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "keepsake_2"}}]},
                  m("pf_m_str_in = 55"), {"run_eocs": "PF_MK_gift", "beta_talker": "avatar"}]},
    ], "u = someone whittling at the fire.  About one evening in three, if they're warm toward you (15+) and you're at the fire, the carving is for you: a keepsake at your feet, and a gift moment strong enough to remember."),
    eoc("PF_FIRE_join", [
        {"run_eocs": "PF_ID_ensure"},
        {"set_string_var": "pf_fire_c_<global_val:pf_fire_n>", "target_var": ctx("ref"), "parse_tags": True},
        {"u_set_talker": {"var_val": "ref"}},
        m(f"_sx = {seat_x}"), m(f"_sy = {seat_y}"),
        {"if": {"and": [{"u_has_trait": "PF_T_LONER"}, m("value_or(pf_eve_home, 0) == 0")]}, "then": [m("_sx *= 2"), m("_sy *= 2"), m("_sy += 1")]},
        {"copy_var": g("pf_fire_loc"), "target_var": {"u_val": "pf_walk_to"}},
        {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("_sx"), "y_adjust": m("_sy")},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
        m("u_pf_fire_seated = pf_eve_day"),
        m("pf_fire_n += 1"),
    ], "u = a nearby NPC.  Takes a seat (u_set_guard_pos is a walk order) and records its character id in pf_fire_c_<n>.  Grown-ups are seated first (pass pf_rc_kids = 0), then children.",
        condition={"and": [m("pf_fire_n < 6"), m("u_has_trait('PF_CHILD') == value_or(pf_rc_kids, 0)")]}),
    eoc("PF_FIRE_pairs_from_i", [
        m("pf_fj = pf_fi + 1"),
        {"run_eocs": "PF_FIRE_pair_ij", "condition": m("pf_fj < pf_fire_n"), "iterations": 10},
        m("pf_fi += 1"),
    ]),
    eoc("PF_FIRE_pair_ij", [
        {"set_string_var": "pf_fire_c_<global_val:pf_fi>", "target_var": ctx("ri"), "parse_tags": True},
        {"set_string_var": "pf_fire_c_<global_val:pf_fj>", "target_var": ctx("rj"), "parse_tags": True},
        {"run_eocs": "PF_FIRE_pair_do", "alpha_talker": {"var_val": "ri"}, "beta_talker": {"var_val": "rj"}},
        m("pf_fj += 1"),
    ]),
    eoc("PF_FIRE_pair_do", [
        {"run_eocs": "PF_ID_ensure"}, {"run_eocs": "PF_ID_ensure", "alpha_talker": "npc"},
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        {"if": m("pf_read_x >= 25"),
         "then": [name_into("pf_say_a"), name_into("pf_say_b", "<npc_name>"),
                  {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "bicker"}},
                  {"run_eocs": "PF_MK_bicker"}],
         "else": [{"if": m("pf_fire_service == 1"), "then": [{"run_eocs": "PF_MK_funeral"}], "else": [{"run_eocs": "PF_MK_fire_evening"}]}]},
    ], "Alpha and beta = two people at the fire.  Friction reads tension: past 25 they bicker (which keeps tension alive) instead of warming to each other."),
    eoc("PF_FIRE_with_avatar_i", [
        {"set_string_var": "pf_fire_c_<global_val:pf_fi>", "target_var": ctx("ri"), "parse_tags": True},
        {"if": m("pf_fire_service == 1"),
         "then": [{"run_eocs": "PF_MK_funeral", "alpha_talker": {"var_val": "ri"}, "beta_talker": "avatar"}],
         "else": [{"run_eocs": "PF_MK_fire_evening", "alpha_talker": {"var_val": "ri"}, "beta_talker": "avatar"}]},
        m("pf_fi += 1"),
    ]),
    eoc("PF_FIRE_recall_i", [
        {"set_string_var": "pf_fire_c_<global_val:pf_fi>", "target_var": ctx("ri"), "parse_tags": True},
        {"run_eocs": "PF_RECALL_try", "alpha_talker": {"var_val": "ri"}},
        m("pf_fi += 1"),
    ]),
    eoc("PF_RECALL_try", [
        {"if": {"or": [{"u_has_effect": "PF_infant"}, m("u_val('age') < 5")]}, "then": [m("pf_rbest_skip = 1")], "else": [m("pf_rbest_skip = 0")]},
        m("pf_ri = 0"), m("pf_rbest = -1"), m("pf_rbest_str = 49 + pf_rbest_skip * 1000"),
        {"run_eocs": "PF_RECALL_scan_i", "condition": m("pf_ri < 8"), "iterations": 9},
        {"if": m("pf_rbest >= 0"), "then": [
            {"set_string_var": "u_pf_mem_<global_val:pf_rbest>_kind", "target_var": ctx("mk"), "parse_tags": True},
            {"set_string_var": "u_pf_mem_<global_val:pf_rbest>_rc", "target_var": ctx("mr"), "parse_tags": True},
            {"set_string_var": "u_pf_mem_<global_val:pf_rbest>_role", "target_var": ctx("mo"), "parse_tags": True},
            m("pf_say_role = value_or(v_mo, 1)"),
            m("v_mr = 1"), m("pf_fire_recalled = 1"), name_into("pf_say_a"),
            {"copy_var": {"var_val": "mk"}, "target_var": g("pf_say_kind")},
            {"run_eocs": "PF_SAY_recall", "alpha_talker": "avatar"},
            {"if": {"compare_string": [g("pf_say_kind"), "insult", "betrayal", "argument"]},
             "then": [{"run_eocs": "PF_MK_bicker", "beta_talker": "avatar"}],
             "else": [{"run_eocs": "PF_MK_memory_recalled", "beta_talker": "avatar"}]}]},
    ], "u = someone at the fire.  The witness system: they bring up their strongest memory about you (strength 50+) that they haven't told yet.  Good memories warm both of you; sore ones reopen tension."),
    eoc("PF_RECALL_scan_i", [
        {"set_string_var": "u_pf_mem_<global_val:pf_ri>_with", "target_var": ctx("mw"), "parse_tags": True},
        {"set_string_var": "u_pf_mem_<global_val:pf_ri>_str", "target_var": ctx("ms"), "parse_tags": True},
        {"set_string_var": "u_pf_mem_<global_val:pf_ri>_rc", "target_var": ctx("mr"), "parse_tags": True},
        {"if": {"and": [{"compare_string": [{"var_val": "mw"}, "AVATAR"]},
                        m("value_or(v_ms, 0) > pf_rbest_str"), m("value_or(v_mr, 0) == 0")]},
         "then": [m("pf_rbest = pf_ri"), m("pf_rbest_str = v_ms")]},
        m("pf_ri += 1"),
    ]),
    eoc("PF_SAY_recall", [
        {"if": {"and": [{"compare_string": [g("pf_say_kind"), "saved_life"]}, m("pf_say_role == 2")]},
         "then": [hsay("<global_val:pf_say_a> stares into the fire.  \"I keep thinking about the day I nearly lost you.  Don't make me do that again.\"", "<global_val:pf_say_a> turns their cup in their hands.  \"I keep thinking about the day I nearly lost you.  Don't make me do that again.\"", "good")],
         "else": [{"if": {"compare_string": [g("pf_say_kind"), "saved_life"]},
         "then": [hsay("<global_val:pf_say_a> stares into the fire.  \"I keep thinking about the day you pulled me out of that.  I owe you.\"", "<global_val:pf_say_a> turns their cup in their hands.  \"I keep thinking about the day you pulled me out of that.  I owe you.\"", "good")],
         "else": [{"if": {"compare_string": [g("pf_say_kind"), "near_death"]},
                   "then": [hsay("<global_val:pf_say_a> pokes at the embers.  \"That thing nearly had you today.  Don't do that to me again.\"", "<global_val:pf_say_a> taps the table.  \"That thing nearly had you today.  Don't do that to me again.\"", "good")],
                   "else": [{"if": {"compare_string": [g("pf_say_kind"), "insult", "argument"]},
                             "then": [say("<global_val:pf_say_a> doesn't look at you.  \"I haven't forgotten what you said.\"", "bad")],
                             "else": [{"if": {"compare_string": [g("pf_say_kind"), "betrayal"]},
                                       "then": [say("<global_val:pf_say_a>, quietly: \"I trusted you.\"", "bad")],
                                       "else": [{"run_eocs": "PF_SAY_recall_kind", "alpha_talker": "avatar"}]}]}]}]}]},
    ]),
    # playtest 3: every daily meal was a "memory", and every evening said the same generic line about it
    eoc("PF_SAY_recall_kind", [m("pf_rk_said = 0"),
        {"if": {"and": [{"compare_string": [g("pf_say_kind"), "meal_shared"]}, m("(pf_say_role == 1) + (pf_say_role == 2) > 0")]}, "then": [m("pf_rk_said = 1"), m("_q = rand(2)"),
            {"if": m("_q == 0"), "then": [say("<global_val:pf_say_a> brings up the day your paths first crossed.  \"You looked like you'd been living out of cans for a week.\"", "good")]},
            {"if": m("_q == 1"), "then": [say("<global_val:pf_say_a> laughs about the time you two split a can of something neither of you could name.", "good")]},
            {"if": m("_q == 2"), "then": [say("<global_val:pf_say_a> says food tastes better when somebody else opened the can.  They mean you.", "good")]}]},
        # full run day 160: Emanuel thanked Dante twice for a bandage he never got; care_given is also supplies, breakfast, tea,
        # a nightmare sat through, so the words have to fit any of them
        {"if": {"and": [m("pf_rk_said == 0"), m("pf_say_role == 1"), {"compare_string": [g("pf_say_kind"), "care_given"]}]}, "then": [m("pf_rk_said = 1"), m("_q = rand(2)"),
            {"if": m("_q == 0"), "then": [say("<global_val:pf_say_a> brings up a day you looked out for them.  \"Didn't say thanks then.  Saying it now.\"", "good")]},
            {"if": m("_q == 1"), "then": [say("<global_val:pf_say_a> remembers, out loud, a time you went out of your way for them, and doesn't make a speech of it.", "good")]},
            {"if": m("_q == 2"), "then": [say("<global_val:pf_say_a>: \"You didn't have to do that, back then.  I keep thinking about it.\"", "good")]}]}] + [
        # only for a memory they were part of (role 1 = it happened to them, 2 = they did it); a witness gets the general line below
        # (playtest 3: Myles, who had only watched Thaddeus being taken in, said "Never thought I'd have a place again")
        {"if": {"and": [m("pf_rk_said == 0"), m("(pf_say_role == 1) + (pf_say_role == 2) * " + ("1" if k in ("shared_danger", "taught") else "0") + " > 0"), {"compare_string": [g("pf_say_kind"), k]}]}, "then": [m("pf_rk_said = 1"), say(t, "good")]}
        for k, t in [

            ("shared_danger", "<global_val:pf_say_a> brings up the fight the other day.  \"You didn't run.  I noticed.\""),
            ("gift", "<global_val:pf_say_a> turns over the thing you gave them, and puts it away again carefully."),
            ("watch_covered", "<global_val:pf_say_a>: \"You took my watch that night.  I slept like the dead.  Well.  You know what I mean.\""),
            ("welcomed", "<global_val:pf_say_a> looks around at the walls.  \"Never thought I'd have a place again.\""),
            ("taught", "<global_val:pf_say_a> shows you they still remember what you taught them, and waits to be told it's right."),
            ("adopted", "<global_val:pf_say_a> leans against you without saying anything, and stays there."),
        ]] + [
        {"if": m("pf_rk_said == 0"), "then": [{"run_eocs": "PF_LINE_retell"}]},
    ], "u = avatar.  The good memory someone brings up at the fire, in words that fit what it was."),
]

# ============================================================ FRICTION  (quirk clash: gallows humor teases; proud takes it badly)
files["friction.json"] = [
    eoc("PF_TEASE_on_throwup", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_tease_victim_uid")},
        {"u_set_talker": g("pf_tease_victim")},
        m("pf_tease_done = 0"),
        {"u_run_npc_eocs": ["PF_TEASE_candidate"], "local": True, "npc_range": 10},
    ], "Bottom-up signal: anyone throws up.  A nearby NPC with gallows humor can't resist.",
        condition={"and": ["has_alpha", cooldown_ok_c("pf_tease_last", "30 m")]},
        eoc_type="EVENT", required_event="throws_up"),
    eoc("PF_TEASE_candidate", [
        {"run_eocs": "PF_ID_ensure"},
        {"if": {"and": [{"u_has_trait": "PF_Q_GALLOWS"}, m("pf_tease_done == 0"),
                        {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_tease_victim_uid")]}}]},
         "then": [m("pf_tease_done = 1"), m("pf_tease_last = time('now')"),
                  name_into("pf_say_a"),
                  {"run_eocs": "PF_TEASE_name_victim", "alpha_talker": g("pf_tease_victim")},
                  {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "tease"}},
                  {"run_eocs": "PF_MK_teased", "beta_talker": g("pf_tease_victim")}]},
    ]),
    eoc("PF_TEASE_name_victim", [{"if": "u_is_avatar",
                                  "then": [{"set_string_var": "you", "target_var": g("pf_say_b")}],
                                  "else": [name_into("pf_say_b")]}]),
]

# ============================================================ BOTTOM-UP SIGNALS  (near death -> witnesses; eating together)
files["signals.json"] = [
    eoc("PF_SIG_near_death", [
        m("pf_neardeath_last = time('now')"),
        m("pf_m_str_in = 70"),
        {"run_eocs": "PF_MK_near_death"},
        {"run_eocs": "PF_HEART_partner_scare"},
    ], "Signal: the avatar takes a hit that leaves the torso or head at 40% or less.  Everyone who saw it gets a near_death memory of you (once an hour at most).",
        condition={"and": ["u_is_avatar",
                           {"or": [m("u_hp('torso') <= u_hp_max('torso') * 0.4"), m("u_hp('head') <= u_hp_max('head') * 0.4")]},
                           cooldown_ok_c("pf_neardeath_last", "1 h")]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    eoc("PF_SIG_meal", [
        m("pf_meal_last = time('now')"),
        {"u_run_npc_eocs": ["PF_SIG_meal_with"], "local": True, "npc_range": 6},
    ], "Signal: the avatar eats with people within 6 tiles.  A meal_shared moment with each (once every 4 hours).",
        condition={"and": ["u_is_avatar", cooldown_ok_c("pf_meal_last", "4 h")]},
        eoc_type="EVENT", required_event="character_eats_item"),
    eoc("PF_SIG_meal_with", [{"run_eocs": "PF_MK_meal_shared", "alpha_talker": "avatar", "beta_talker": "u"}]),
]

# ============================================================ COMBAT  (playtest gap: fighting side by side recorded nothing)
files["combat.json"] = [
    eoc("PF_COMBAT_kill", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kill_uid")},
        {"u_set_talker": g("pf_kill_who")},
        {"u_location_variable": g("pf_kill_pos")},
        {"copy_var": g("pf_kill_pos"), "target_var": g("pf_kill_mpos")},
        {"if": "has_beta", "then": [{"npc_location_variable": g("pf_kill_mpos")}]},
        {"if": {"compare_string": [ctx("lab_victim"), "set"]}, "then": [{"copy_var": g("pf_ll_vpos"), "target_var": g("pf_kill_mpos")}]},
        {"if": m("value_or(pf_eve_state, 0) == 1"), "then": [{"run_eocs": "PF_FIRE_scatter", "alpha_talker": "avatar"}]},
        {"if": cooldown_ok_c("u_pf_kill_last", "10 m"), "then": [
            m("u_pf_kill_last = time('now')"),
            {"u_run_npc_eocs": ["PF_COMBAT_comrade"], "local": True, "npc_range": 8},
            {"if": {"not": "u_is_avatar"}, "then": [{"run_eocs": "PF_COMBAT_comrade_avatar", "alpha_talker": "avatar"}]}]},
        {"run_eocs": "PF_COMBAT_rescue_check", "alpha_talker": "avatar"},
        {"u_run_npc_eocs": ["PF_COMBAT_rescue_check"], "local": True, "npc_range": 30},
    ], "Bottom-up signal: someone kills a monster (alpha = killer, beta = the dead monster).  (1) A fight breaks up the fire.  (2) Everyone fighting within 8 tiles shared the danger with the killer (once per fight: 10 minutes per killer).  (3) Anyone the thing was on (within 1 tile of it) who was hurt, grabbed, or hit by a monster in the last minute (PF_RK_hurt) was saved by the killer, whoever they are: NPC saves you, you save an NPC, NPC saves NPC.",
        condition={"and": ["has_alpha", {"or": ["u_is_avatar", "u_is_npc"]}]},
        eoc_type="EVENT", required_event="character_kills_monster"),
    eoc("PF_COMBAT_comrade_avatar", [
        {"u_location_variable": g("pf_kill_av_pos")},
        {"if": m("distance(pf_kill_av_pos, pf_kill_pos) <= 8"),
         "then": [{"run_eocs": "PF_MK_shared_danger", "alpha_talker": g("pf_kill_who"), "beta_talker": "u"}]},
    ], "u = avatar, when an NPC made the kill."),
    eoc("PF_COMBAT_comrade", [
        {"run_eocs": "PF_ID_ensure"},
        {"if": {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kill_uid")]}},
         "then": [{"run_eocs": "PF_MK_shared_danger", "alpha_talker": g("pf_kill_who"), "beta_talker": "u"}]},
    ], "u = someone within 8 tiles of the killer (not the killer)."),
    eoc("PF_COMBAT_rescue_check", [
        {"run_eocs": "PF_ID_ensure"},
        {"if": {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kill_uid")]}}, "then": [
            {"u_location_variable": {"u_val": "pf_pos"}},
            {"if": m("distance(u_pf_pos, pf_kill_mpos) <= 1"), "then": [
                m("u_pf_saved_last = time('now')"),
                {"run_eocs": "PF_SAVE_record", "alpha_talker": g("pf_kill_who"), "beta_talker": "u"}]}]},
    ], "u = you or a nearby NPC.  Were they the one the thing was on, and in trouble?",
        condition={"and": [{"or": [HURT, {"u_has_effect": "grabbed"}, m("value_or(u_pf_hurt_t, -1) >= time('now') - time('1 m')")]},
                           cooldown_ok_c("u_pf_saved_last", "1 h")]}),
    eoc("PF_SAVE_record", [
        {"run_eocs": "PF_ID_ensure"}, {"run_eocs": "PF_ID_ensure", "alpha_talker": "npc"},
        {"set_string_var": "n_pf_debt_<u_val:pf_uid>", "target_var": ctx("dv"), "parse_tags": True},
        {"set_string_var": "u_pf_debt_<npc_val:pf_uid>", "target_var": ctx("ds"), "parse_tags": True},
        m("v_dv += 1"), m("v_ds -= 1"),
        m("pf_save_d = v_dv"), m("pf_save_n = pf_save_d < 0 ? 0 - pf_save_d : pf_save_d"),
        name_into("pf_say_a"), name_into("pf_say_b", "<npc_name>"),
        {"if": "npc_is_avatar", "then": [m("pf_save_case = 1")],
         "else": [{"if": "u_is_avatar", "then": [m("pf_save_case = 2")], "else": [m("pf_save_case = 3")]}]},
        {"run_eocs": "PF_SAY_save", "alpha_talker": "avatar"},
        {"run_eocs": "PF_RK_note_rescue"},
        m("pf_m_str_in = 75"), {"run_eocs": "PF_MK_saved_life"},
    ], "Alpha = the one who saved, beta = the one saved.  The ledger is two-way: the saved one's u_pf_debt_<saver> goes up, the saver's u_pf_debt_<saved> goes down, so each side knows the running score (who owes whom, and how many times).  The lines read it."),
]

SCAN_J_LIST = [{"if": {"and": [{"math": ["pf_fire_n > 0"]}, {"math": ["pf_fi != 0"]}]}, "then": [{"copy_var": {"global_val": "pf_fire_u_0"}, "target_var": {"global_val": "pf_m_other"}}, {"run_eocs": "PF_VIEW_read"}, {"if": {"math": ["pf_read_a > pf_rom_best"]}, "then": [{"math": ["pf_rom_best = pf_read_a"]}, {"math": ["pf_rom_bw = pf_read_w"]}, {"math": ["pf_rom_bj = 0"]}, {"copy_var": {"global_val": "pf_fire_u_0"}, "target_var": {"global_val": "pf_rom_buid"}}]}, {"if": {"compare_string": [{"u_val": "pf_sweet"}, {"global_val": "pf_fire_u_0"}]}, "then": [{"math": ["pf_rom_sj = 0"]}]}]}, {"if": {"and": [{"math": ["pf_fire_n > 1"]}, {"math": ["pf_fi != 1"]}]}, "then": [{"copy_var": {"global_val": "pf_fire_u_1"}, "target_var": {"global_val": "pf_m_other"}}, {"run_eocs": "PF_VIEW_read"}, {"if": {"math": ["pf_read_a > pf_rom_best"]}, "then": [{"math": ["pf_rom_best = pf_read_a"]}, {"math": ["pf_rom_bw = pf_read_w"]}, {"math": ["pf_rom_bj = 1"]}, {"copy_var": {"global_val": "pf_fire_u_1"}, "target_var": {"global_val": "pf_rom_buid"}}]}, {"if": {"compare_string": [{"u_val": "pf_sweet"}, {"global_val": "pf_fire_u_1"}]}, "then": [{"math": ["pf_rom_sj = 1"]}]}]}, {"if": {"and": [{"math": ["pf_fire_n > 2"]}, {"math": ["pf_fi != 2"]}]}, "then": [{"copy_var": {"global_val": "pf_fire_u_2"}, "target_var": {"global_val": "pf_m_other"}}, {"run_eocs": "PF_VIEW_read"}, {"if": {"math": ["pf_read_a > pf_rom_best"]}, "then": [{"math": ["pf_rom_best = pf_read_a"]}, {"math": ["pf_rom_bw = pf_read_w"]}, {"math": ["pf_rom_bj = 2"]}, {"copy_var": {"global_val": "pf_fire_u_2"}, "target_var": {"global_val": "pf_rom_buid"}}]}, {"if": {"compare_string": [{"u_val": "pf_sweet"}, {"global_val": "pf_fire_u_2"}]}, "then": [{"math": ["pf_rom_sj = 2"]}]}]}, {"if": {"and": [{"math": ["pf_fire_n > 3"]}, {"math": ["pf_fi != 3"]}]}, "then": [{"copy_var": {"global_val": "pf_fire_u_3"}, "target_var": {"global_val": "pf_m_other"}}, {"run_eocs": "PF_VIEW_read"}, {"if": {"math": ["pf_read_a > pf_rom_best"]}, "then": [{"math": ["pf_rom_best = pf_read_a"]}, {"math": ["pf_rom_bw = pf_read_w"]}, {"math": ["pf_rom_bj = 3"]}, {"copy_var": {"global_val": "pf_fire_u_3"}, "target_var": {"global_val": "pf_rom_buid"}}]}, {"if": {"compare_string": [{"u_val": "pf_sweet"}, {"global_val": "pf_fire_u_3"}]}, "then": [{"math": ["pf_rom_sj = 3"]}]}]}, {"if": {"and": [{"math": ["pf_fire_n > 4"]}, {"math": ["pf_fi != 4"]}]}, "then": [{"copy_var": {"global_val": "pf_fire_u_4"}, "target_var": {"global_val": "pf_m_other"}}, {"run_eocs": "PF_VIEW_read"}, {"if": {"math": ["pf_read_a > pf_rom_best"]}, "then": [{"math": ["pf_rom_best = pf_read_a"]}, {"math": ["pf_rom_bw = pf_read_w"]}, {"math": ["pf_rom_bj = 4"]}, {"copy_var": {"global_val": "pf_fire_u_4"}, "target_var": {"global_val": "pf_rom_buid"}}]}, {"if": {"compare_string": [{"u_val": "pf_sweet"}, {"global_val": "pf_fire_u_4"}]}, "then": [{"math": ["pf_rom_sj = 4"]}]}]}, {"if": {"and": [{"math": ["pf_fire_n > 5"]}, {"math": ["pf_fi != 5"]}]}, "then": [{"copy_var": {"global_val": "pf_fire_u_5"}, "target_var": {"global_val": "pf_m_other"}}, {"run_eocs": "PF_VIEW_read"}, {"if": {"math": ["pf_read_a > pf_rom_best"]}, "then": [{"math": ["pf_rom_best = pf_read_a"]}, {"math": ["pf_rom_bw = pf_read_w"]}, {"math": ["pf_rom_bj = 5"]}, {"copy_var": {"global_val": "pf_fire_u_5"}, "target_var": {"global_val": "pf_rom_buid"}}]}, {"if": {"compare_string": [{"u_val": "pf_sweet"}, {"global_val": "pf_fire_u_5"}]}, "then": [{"math": ["pf_rom_sj = 5"]}]}]}]
# ============================================================ ROMANCE  (v0.1: their own hearts.  Attraction lives in the spine; this is who acts on it)
files["romance.json"] = [
    eoc("PF_ROM_fire_i", [
        {"set_string_var": "pf_fire_c_<global_val:pf_fi>", "target_var": ctx("ri"), "parse_tags": True},
        {"run_eocs": "PF_ROM_fire_one", "alpha_talker": {"var_val": "ri"}},
        m("pf_fi += 1"),
    ]),
    eoc("PF_ROM_fire_one", [
        m("pf_rom_best = 0"), m("pf_rom_bj = -9"), m("pf_rom_sj = -9"), m("pf_rom_bw = 0"),
    ] + SCAN_J_LIST + [
        {"if": {"and": [m("pf_fire_av_here"), m("value_or(pf_set_romance, 2) == 2")]}, "then": [
            {"set_string_var": "AVATAR", "target_var": g("pf_m_other")},
            {"run_eocs": "PF_VIEW_read"},
            {"if": m("pf_read_a > pf_rom_best"), "then": [
                m("pf_rom_best = pf_read_a"), m("pf_rom_bw = pf_read_w"), m("pf_rom_bj = -1"),
                {"set_string_var": "AVATAR", "target_var": g("pf_rom_buid")}]},
            {"if": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}, "then": [m("pf_rom_sj = -1")]}]},
        name_into("pf_say_a"),
        # sweethearts sit together
        {"if": m("pf_rom_sj == -1"), "then": [
            m("pf_rom_done += 1"),
            {"run_eocs": "PF_LINE_court_you", "alpha_talker": "avatar"},
            {"run_eocs": "PF_HEART_together", "alpha_talker": "avatar"},
            {"run_eocs": "PF_MK_courting", "beta_talker": "avatar"}],
         "else": [{"if": m("pf_rom_sj >= 0"), "then": [
            m("pf_rom_done += 1"), {"set_string_var": "court", "target_var": g("pf_rom_what")}, {"run_eocs": "PF_ROM_with_j"}],
         # no sweetheart here: a confession, or just glances
         "else": [{"if": {"and": [m("pf_rom_best >= 60"), m("pf_rom_bw >= 35"), m("value_or(u_pf_has_sweet, 0) == 0"),
                                  cooldown_ok_c("u_pf_conf_last", "7 d")]},
                   "then": [m("pf_rom_done += 1"), m("u_pf_conf_last = time('now')"),
                            {"if": m("pf_rom_bj == -1"),
                             "then": [{"if": m("value_or(pf_set_romance, 2) == 2"), "then": [{"u_set_talker": g("pf_conf_who")}, {"set_string_var": "<u_name>", "target_var": g("pf_conf_name"), "parse_tags": True}, {"run_eocs": "PF_ROM_open_confess", "alpha_talker": "avatar", "beta_talker": "u"}]}],
                             "else": [{"set_string_var": "confess", "target_var": g("pf_rom_what")}, {"run_eocs": "PF_ROM_with_j"}]}],
                   # full run days 177-180: "You catch Mitzi Nunes making eyes at Consuelo Porter." four evenings running.
                   # One glance per looker every 3 days (the lab's forced glance still works).
                   "else": [{"if": {"and": [m("pf_rom_best >= 30"), m("value_or(pf_set_chatter, 1) == 1"), m("(rand(1) == 0) + value_or(pf_rom_force_glance, 0) > 0"),
                                                   m("(value_or(u_pf_has_sweet, 0) == 0) + (value_or(u_pf_commit, 1) == 3) > 0"),
                                                   m("(time('now') - value_or(u_pf_glance_t, -999999) >= time('3 d')) + value_or(pf_rom_force_glance, 0) > 0")]}, "then": [
                       m("pf_rom_force_glance = 0"), m("u_pf_glance_t = time('now')"),
                       m("pf_rom_done += 1"),
                       {"if": m("pf_rom_bj == -1"),
                        "then": [{"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "smitten_you"}},
                                 {"run_eocs": "PF_MK_flirt", "beta_talker": "avatar"},
                                 {"run_eocs": "PF_HEART_jealousy", "beta_talker": "avatar"}],
                        "else": [{"set_string_var": "glance", "target_var": g("pf_rom_what")}, {"run_eocs": "PF_ROM_with_j"}]}]}]}]}]},
    ], "u = someone at the fire (a romantic adult, not feeling awkward).  Looks at who's here through their own eyes: if their sweetheart is here, the two sit apart together; if they've fallen hard (attraction 60+, warmth 35+) they confess, to you through a conversation or to another; if they're smitten (30+) they keep glancing over.  At most two romance beats per evening, so it stays special.",
        condition={"and": [m("value_or(u_pf_rom, 0) == 1"), m("value_or(u_pf_adult, 0) == 1"), {"not": {"u_has_trait": "PF_CHILD"}},
                           m("time('now') > value_or(u_pf_awk_until, 0)"), m("value_or(u_pf_rom_beat, -1) != pf_beat_id"),
                           {"not": m("time('now') < value_or(u_pf_mourn_until, 0)")}]}),
    eoc("PF_ROM_with_j", [
        {"set_string_var": "pf_fire_c_<global_val:pf_rom_bj>", "target_var": ctx("rj"), "parse_tags": True},
        {"if": {"compare_string": [g("pf_rom_what"), "court"]}, "then": [
            {"set_string_var": "pf_fire_c_<global_val:pf_rom_sj>", "target_var": ctx("rj"), "parse_tags": True}]},
        {"run_eocs": "PF_ROM_pair", "beta_talker": {"var_val": "rj"}},
    ], "u = the one acting; finds the other fire-goer's talker (same turn as the roll call, so it's valid)."),
    eoc("PF_ROM_pair", [
        m("u_pf_rom_beat = pf_beat_id"), m("n_pf_rom_beat = pf_beat_id"),
        name_into("pf_say_a"), name_into("pf_say_b", "<npc_name>"),
        {"if": {"compare_string": [g("pf_rom_what"), "court"]}, "then": [
            {"run_eocs": "PF_LINE_court_npc", "alpha_talker": "avatar"},
            {"run_eocs": "PF_MK_courting"}]},
        {"if": {"compare_string": [g("pf_rom_what"), "glance"]}, "then": [
            {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "smitten"}},
            {"run_eocs": "PF_MK_flirt"},
            {"run_eocs": "PF_HEART_jealousy"}]},
        {"if": {"compare_string": [g("pf_rom_what"), "confess"]}, "then": [
            {"run_eocs": "PF_ROM_answer_npc", "alpha_talker": "npc", "beta_talker": "u"},
            {"run_eocs": "PF_MK_confession"},
            {"if": m("pf_rom_yes == 1"),
             "then": [{"run_eocs": "PF_ROM_become_sweet"},
                      {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "confess_yes"}},
                      {"run_eocs": "PF_MK_courting"}],
             "else": [m("u_pf_awk_until = time('now') + time('3 d')"),
                      {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "confess_no_npc"}},
                      {"run_eocs": "PF_MK_rejected", "alpha_talker": "npc", "beta_talker": "u"}]}]},
    ], "Alpha = the one who feels it, beta = the one they feel it for (both at the fire)."),
    eoc("PF_ROM_answer_npc", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("pf_rom_yes = (pf_read_a >= 40) * (value_or(u_pf_has_sweet, 0) == 0) * (time('now') >= value_or(u_pf_mourn_until, 0))"),
        {"set_string_var": "gentle", "target_var": g("pf_rom_how")},
        {"if": {"u_has_trait": "PF_T_LONER"}, "then": [{"set_string_var": "blunt", "target_var": g("pf_rom_how")}]},
    ], "u = the one being confessed to (npc = the confessor).  They answer from their own heart: yes only if they feel it too (attraction 40+), aren't taken and aren't mourning.  Loners say no bluntly."),
    eoc("PF_ROM_become_sweet", [
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": {"u_val": "pf_sweet"}}, m("u_pf_has_sweet = 1"), m("u_pf_sweet_since = time('now')"),
        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"npc_val": "pf_sweet"}}, m("n_pf_has_sweet = 1"), m("n_pf_sweet_since = time('now')"),
        m("u_pf_rel_stage = 1"), m("n_pf_rel_stage = 1"), m("u_pf_stage_since = time('now')"), m("n_pf_stage_since = time('now')"),
        m("pf_couples_total = value_or(pf_couples_total, 0) + 1"),
    ], "Alpha and beta become sweethearts (courting; v0.2 turns this into partnership and marriage)."),
    eoc("PF_ROM_open_confess", [{"open_dialogue": {"topic": "TALK_PF_CONFESS"}}],
        "Alpha = avatar.  A dialogue opened with a topic talks to an empty talker, not the NPC, so the confessor is kept in pf_conf_who (set this same turn) and the answers act on it."),
    eoc("PF_ROM_you_yes", [
        {"run_eocs": "PF_ROM_become_sweet"},
        {"run_eocs": "PF_MK_confession", "alpha_talker": "npc", "beta_talker": "u"},
        {"run_eocs": "PF_MK_courting", "alpha_talker": "npc", "beta_talker": "u"},
        say("<npc_name> lets out a breath they've been holding for weeks.", "good"),
    ], "In the confession dialogue: u = you, npc = them."),
    eoc("PF_ROM_you_no", [
        {"run_eocs": "PF_MK_confession", "alpha_talker": "npc", "beta_talker": "u"},
        {"run_eocs": "PF_MK_rejected", "beta_talker": "npc"},
        m("n_pf_awk_until = time('now') + time('3 d')"),
        say("<npc_name> nods, too quickly.  \"Okay.  I just… needed to say it.\"", "info"),
    ]),
    eoc("PF_ROM_you_wait", [say("<npc_name>: \"Take all the time you need.  I'm not going anywhere.\"", "info")]),
    # ---- the player acts (People menu)
    eoc("PF_ROM_flirt", [
        {"run_eocs": "PF_ROM_their_heart", "alpha_talker": "npc"},
        {"if": m("pf_rom_el == 0"),
         "then": [say("<npc_name> doesn't seem to notice you're flirting.", "info")],
         "else": [{"if": m("pf_read_a + rand(20) >= 20"),
                   "then": [say("<npc_name> laughs, and doesn't look away.", "good"), {"run_eocs": "PF_MK_flirt", "beta_talker": "npc"}],
                   "else": [say("<npc_name> smiles politely and changes the subject.", "info")]}]},
        m("n_pf_flirted = time('now')"),
    ], "u = you, npc = them.  Whether it lands depends on them: their nature (are they drawn to you at all?) and how they already feel.",
        condition=cooldown_ok_c("n_pf_flirted", "1 h")),
    eoc("PF_ROM_confess_you", [
        {"run_eocs": "PF_ROM_their_heart", "alpha_talker": "npc"},
        {"if": {"compare_string": [{"npc_val": "pf_sweet"}, "AVATAR"]},
         "then": [say("<npc_name> grins.  \"You already did.  I was there.\"", "good")],
         "else": [{"if": {"and": [m("time('now') < value_or(n_pf_mourn_until, 0)"), m("value_or(n_pf_has_sweet, 0) == 0"), m("pf_rom_el == 1")]},
                   "then": [say("<npc_name> holds your hand for a moment, then gives it back.  \"Not now.  Ask me again when I can breathe.\"", "info")],
                   "else": [{"run_eocs": "PF_ROM_confess_you_ans"}]}]},
    ], "u = you, npc = them.  Someone still mourning asks you to wait (no rejection, no answer yet).  Otherwise they answer from their own heart; some can be won over in time (open natures warm up as warmth grows), some never will."),
    eoc("PF_ROM_confess_you_ans", [
        {"run_eocs": "PF_MK_confession", "beta_talker": "npc"},
        {"if": {"and": [m("pf_rom_el == 1"), m("pf_read_a >= 45"), m("value_or(n_pf_has_sweet, 0) == 0")]},
         "then": [{"run_eocs": "PF_ROM_become_sweet"}, {"run_eocs": "PF_MK_courting", "beta_talker": "npc"},
                  say("<npc_name> goes quiet, then takes your hand.  \"I was hoping you'd say that.\"", "good")],
         "else": [{"run_eocs": "PF_MK_rejected", "alpha_talker": "npc", "beta_talker": "u"},
                  {"if": m("value_or(n_pf_has_sweet, 0) == 1"),
                   "then": [say("<npc_name> looks away.  \"I'm with someone.  You know that.\"", "bad")],
                   "else": [{"if": m("pf_rom_el == 0"),
                             "then": [{"if": m("pf_rom_aro == 1"),
                                       "then": [say("<npc_name> smiles, a little sadly.  \"It's not you.  I'm just not… like that.  With anyone.\"", "info")],
                                       "else": [say("<npc_name> looks surprised, then kind.  \"You're sweet.  But I'm not drawn to you that way.  I'm sorry.\"", "info")]}],
                             "else": [{"if": {"compare_string": [g("pf_rom_how"), "blunt"]},
                                       "then": [say("<npc_name> shakes their head.  \"No.  Sorry.\"", "bad")],
                                       "else": [say("<npc_name> looks at you for a long moment.  \"I'm sorry.  I don't feel that way.  But I'm glad you told me.\"", "info")]}]}]}]},
    ], "u = you, npc = them (PF_ROM_confess_you, not mourning)."),
    eoc("PF_ROM_their_heart", [
        {"run_eocs": "PF_ID_ensure", "alpha_talker": "avatar"},
        {"run_eocs": "PF_ID_ensure"},
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        {"set_string_var": "pf_reg_AVATAR_g", "target_var": ctx("ag"), "parse_tags": True},
        m("pf_rom_el = (value_or(u_pf_rom, 0) == 1) * (value_or(u_pf_adult, 0) == 1) * ((value_or(u_pf_orient, -1) == 2) + (value_or(u_pf_orient, -1) == value_or(v_ag, -2)) > 0)"),
        {"if": {"u_has_trait": "PF_CHILD"}, "then": [m("pf_rom_el = 0")]},
        m("pf_rom_aro = value_or(u_pf_rom, 0) == 0"),
        {"set_string_var": "gentle", "target_var": g("pf_rom_how")},
        {"if": {"u_has_trait": "PF_T_LONER"}, "then": [{"set_string_var": "blunt", "target_var": g("pf_rom_how")}]},
    ], "u = the NPC.  How they feel about you (pf_read_*), and whether you could ever be what they're drawn to (pf_rom_el)."),
]

files["romance.json"].append({
    "type": "talk_topic", "id": "TALK_PF_CONFESS",
    "//": "full run day 86: the window showed no speaker (a topic-based open_dialogue talks to an empty talker), so the name is in the line.",
    # full run day 93: Evan confessed while Mariano was already Dante's sweetheart, with the same words as to someone free, and a
    # "yes" would have made a second sweetheart.  When you're with someone, they know it, and the yes becomes "I'm with someone".
    "dynamic_line": {"math": ["value_or(u_pf_has_sweet, 0) == 1"],
                     "yes": "*<global_val:pf_conf_name> looks at the fire, then at you*  I know you're with someone.  I know.  I'm saying it anyway, so it's been said: I like you.  More than like.  You don't have to say anything back.",
                     "no": "*<global_val:pf_conf_name> looks at the fire, then at you*  I keep trying to find a good way to say this, and there isn't one.  I like you.  More than like.  You don't have to say anything back."},
    "responses": [
        {"text": "I feel the same way.", "condition": {"math": ["value_or(u_pf_has_sweet, 0) == 0"]},
         "effect": {"run_eocs": "PF_ROM_you_yes", "alpha_talker": "avatar", "beta_talker": g("pf_conf_who")}, "topic": "TALK_DONE"},
        {"text": "I'm with someone.  I'm sorry.", "condition": {"math": ["value_or(u_pf_has_sweet, 0) == 1"]},
         "effect": {"run_eocs": "PF_ROM_you_no", "alpha_talker": "avatar", "beta_talker": g("pf_conf_who")}, "topic": "TALK_DONE"},
        {"text": "I'm sorry.  I don't feel that way about you.", "effect": {"run_eocs": "PF_ROM_you_no", "alpha_talker": "avatar", "beta_talker": g("pf_conf_who")}, "topic": "TALK_DONE"},
        {"text": "Can I think about it?", "effect": {"run_eocs": "PF_ROM_you_wait", "alpha_talker": "avatar", "beta_talker": g("pf_conf_who")}, "topic": "TALK_DONE"}]})

# ============================================================ SOCIAL  (off-screen life: bands bond while you're away; the living remember the dead)
TODAY = "floor(time('now') / time('1 d'))"
def sb_gather():
    """u = band leader.  Lists the band (leader first) in global strings pf_sb_0..5 and the count in pf_sb_n."""
    eff = [m("pf_sb_n = 1"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_sb_0")}]
    for k in range(5):
        eff.append({"if": {"not": {"compare_string": [{"u_val": f"pf_member_{k}"}, "none"]}}, "then": [
            {"set_string_var": "pf_sb_<global_val:pf_sb_n>", "target_var": ctx("ref"), "parse_tags": True},
            {"copy_var": {"u_val": f"pf_member_{k}"}, "target_var": {"var_val": "ref"}},
            m("pf_sb_n += 1")]})
    return eff
eve_viewer = [{"run_eocs": "PF_ID_ensure"}]
for j in range(6):
    eve_viewer.append({"if": {"and": [m(f"pf_sb_n > {j}"), m(f"pf_sb_self != {j}")]}, "then": [
        {"copy_var": g(f"pf_sb_{j}"), "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("pf_mv_role = 1"),
        {"if": m("pf_read_x >= 25"), "then": [{"run_eocs": "PF_MV_bicker"}], "else": [{"run_eocs": "PF_MV_fire_evening"}]},
        {"if": {"compare_string": [{"u_val": "pf_sweet"}, g(f"pf_sb_{j}")]}, "then": [{"run_eocs": "PF_MV_courting"}, m("pf_bc_calls = value_or(pf_bc_calls, 0) + 1"), {"run_eocs": "PF_FAM_band_conceive"}]},
        {"run_eocs": "PF_VIEW_read"},
        {"if": m("pf_read_a > pf_sbr_best"), "then": [m("pf_sbr_best = pf_read_a"), m(f"pf_sbr_bj = {j}")]}]})
eve_viewer.insert(1, m("pf_sbr_best = 0"))
eve_viewer.insert(2, m("pf_sbr_bj = -1"))
eve_viewer.append({"run_eocs": "PF_HEART_band_viewer"})
eve_viewer.append({"if": {"and": [m("value_or(pf_set_romance, 2) >= 1"), m("pf_sbr_best >= 60"), m("value_or(u_pf_has_sweet, 0) == 0"), m("value_or(u_pf_rom, 0) == 1"),
                                  m("value_or(u_pf_adult, 0) == 1"), {"not": {"u_has_trait": "PF_CHILD"}}, cooldown_ok_c("u_pf_conf_last", "7 d")]},
                   "then": [m("u_pf_conf_last = time('now')"),
                            {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_sbr_from")},
                            {"set_string_var": "pf_sb_<global_val:pf_sbr_bj>", "target_var": ctx("tref"), "parse_tags": True},
                            {"copy_var": {"var_val": "tref"}, "target_var": g("pf_sbr_to")},
                            m("pf_sbr_yes = 0"),
                            {"u_run_npc_eocs": ["PF_SOCIAL_rom_answer"], "unique_ids": [{"var_val": "tref"}], "local": False},
                            {"copy_var": g("pf_sbr_to"), "target_var": g("pf_m_other")},
                            m("pf_mv_role = 2"), {"run_eocs": "PF_MV_confession"},
                            {"if": m("pf_sbr_yes == 1"),
                             "then": [{"copy_var": g("pf_sbr_to"), "target_var": {"u_val": "pf_sweet"}}, m("u_pf_has_sweet = 1"), m("u_pf_sweet_since = time('now')"),
                                      m("u_pf_rel_stage = 1"), m("u_pf_stage_since = time('now')"),
                                      m("pf_mv_role = 1"), {"run_eocs": "PF_MV_courting"},
                                      m("pf_couples_total = value_or(pf_couples_total, 0) + 1")],
                             "else": [m("pf_mv_role = 1"), {"run_eocs": "PF_MV_rejected"},
                                      m("u_pf_awk_until = time('now') + time('3 d')"),
                                      m("pf_rejections_total = value_or(pf_rejections_total, 0) + 1")]}]})
band_eve = [m(f"u_pf_social_day = {TODAY}")] + sb_gather()
for i in range(6):
    band_eve.append({"if": m(f"pf_sb_n > {max(i, 1)}"),  # member i exists, and the band has at least 2 people
                     "then": [m(f"pf_sb_self = {i}"),
                              {"u_run_npc_eocs": ["PF_SOCIAL_eve_viewer"], "unique_ids": [g(f"pf_sb_{i}")], "local": False}]})
band_eve.append(m("pf_social_evenings_total = value_or(pf_social_evenings_total, 0) + 1"))
band_eve.append({"run_eocs": "PF_ROAD_day"})   # v0.7 (gen_away.py): danger on the road
grief_band = []
for k in range(5):
    grief_band.append({"if": {"not": {"compare_string": [{"u_val": f"pf_member_{k}"}, "none"]}},
                       "then": [{"u_run_npc_eocs": ["PF_GRIEF_one"], "unique_ids": [{"u_val": f"pf_member_{k}"}], "local": False}]})
hunt_viewer = [{"run_eocs": "PF_ID_ensure"}]
for j in range(6):
    hunt_viewer.append({"if": {"and": [m(f"pf_sb_n > {j}"), m(f"pf_sb_self != {j}")]}, "then": [
        {"copy_var": g(f"pf_sb_{j}"), "target_var": g("pf_m_other")},
        m("pf_mv_role = 1"), m("pf_m_str_in = pf_sb_hunt_str"), {"run_eocs": "PF_MV_shared_danger"}]})
band_hunt = [m("u_pf_hunt_last = time('now')")] + sb_gather() + [m("pf_sb_hunt_str = rand(7) == 0 ? 60 : 30")]
for i in range(6):
    band_hunt.append({"if": m(f"pf_sb_n > {max(i, 1)}"),
                      "then": [m(f"pf_sb_self = {i}"),
                               {"u_run_npc_eocs": ["PF_SOCIAL_hunt_viewer"], "unique_ids": [g(f"pf_sb_{i}")], "local": False}]})
band_hunt.append(m("pf_social_hunts_total = value_or(pf_social_hunts_total, 0) + 1"))
files["social.json"] = [
    eoc("PF_SOCIAL_band_evening", band_eve,
        "u = an off-screen band leader, once a day after 20:00 (called from the A-Life offline step).  The band makes camp: every member's view of every other member gets a fire_evening half moment, or bicker if tension is 25+.  Up to 6 people = 30 view updates, reached one at a time by unique id.  Pure var math: nothing in the world loads.  So a band you meet already has a history."),
    eoc("PF_SOCIAL_band_hunt", band_hunt,
        "u = an off-screen band leader whose band just finished a leg of its hunt (called from PF_ALIFE_next_waypoint while offline).  At most once per 6 hours: short patrols reach waypoints every few minutes, and the natural playtest logged 492 hunts in 95 minutes without this.  Everyone shared the danger: a mild bond (strength 30), and about one hunt in eight was a close call they'll remember (60).",
        condition=cooldown_ok_c("u_pf_hunt_last", "6 h")),
    eoc("PF_SOCIAL_hunt_viewer", hunt_viewer, "u = one band member (by unique id).  Their view of each of the others gets shared_danger."),
    eoc("PF_SOCIAL_eve_viewer", eve_viewer, "u = one band member (reached by unique id), index pf_sb_self in the band list.  Updates their view of each of the others."),
    eoc("PF_SOCIAL_rom_answer", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": g("pf_sbr_from"), "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("pf_sbr_yes = (pf_read_a >= 40) * (value_or(u_pf_has_sweet, 0) == 0)"),
        m("pf_mv_role = 1"), {"run_eocs": "PF_MV_confession"},
        {"if": m("pf_sbr_yes == 1"),
         "then": [{"copy_var": g("pf_sbr_from"), "target_var": {"u_val": "pf_sweet"}}, m("u_pf_has_sweet = 1"), m("u_pf_sweet_since = time('now')"),
                  m("u_pf_rel_stage = 1"), m("u_pf_stage_since = time('now')"),
                  m("pf_mv_role = 1"), {"run_eocs": "PF_MV_courting"}],
         "else": [m("pf_mv_role = 2"), {"run_eocs": "PF_MV_rejected"}]},
    ], "u = a band member someone just confessed to, off-screen (reached by unique id).  Answers from their own heart, like at the fire."),
    eoc("PF_SOCIAL_on_death", [
        m("pf_grief_before = value_or(pf_grief_total, 0)"),
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_dead_uid")},
        m("pf_dead_band = value_or(u_pf_band, 0)"),
        {"set_string_var": "pf_name_<u_val:pf_uid>", "target_var": ctx("ref"), "parse_tags": True},
        {"set_string_var": "<u_name>", "target_var": {"var_val": "ref"}, "parse_tags": True},
        name_into("pf_dead_name"),
        m("pf_grief_local = 1"), m("pf_grief_shown = 0"),
        {"u_run_npc_eocs": ["PF_GRIEF_one"], "local": True, "npc_range": 60},
        m("pf_grief_local = 0"),
        {"if": m("value_or(u_pf_is_leader, 0) == 1"), "then": grief_band,
         "else": [{"if": m("has_var(u_pf_leader)"), "then": [
             {"u_run_npc_eocs": ["PF_GRIEF_one", "PF_GRIEF_leaders_band"], "unique_ids": [{"u_val": "pf_leader"}], "local": False}]}]},
        {"run_eocs": "PF_HEART_avatar_grief", "alpha_talker": "avatar"},
        {"if": {"or": [m("value_or(pf_grief_total, 0) > pf_grief_before"), m("pf_av_grieved == 1")]}, "then": [
            m("pf_unmourned = 1"), m("pf_unburied = 1"), m("pf_unmourned_t = time('now')"),
            {"copy_var": g("pf_dead_uid"), "target_var": g("pf_unmourned_uid")},
            {"copy_var": g("pf_dead_name"), "target_var": g("pf_unmourned_name")},
            {"run_eocs": "PF_HEART_event_death"}]},
    ], "Someone known by name died (u = the dead).  Remembers their name (pf_name_<uid>) for later lines.  Everyone who cared about them, nearby or in their band far away, keeps a memory of losing them.",
        condition={"and": ["has_alpha", "u_is_npc", m("has_var(u_pf_uid)")]},
        eoc_type="EVENT", required_event="character_dies"),
    eoc("PF_GRIEF_leaders_band", grief_band, "u = the dead member's leader.  Their other band members grieve too (wherever they are)."),
    eoc("PF_GRIEF_one", [
        {"set_string_var": "u_pf_griev_<global_val:pf_dead_uid>", "target_var": ctx("gref"), "parse_tags": True},
        {"if": m("value_or(v_gref, 0) == 0"), "then": [
            m("v_gref = 1"),
            {"run_eocs": "PF_FAM_parent_check"},
            {"copy_var": g("pf_dead_uid"), "target_var": g("pf_m_other")},
            {"run_eocs": "PF_VIEW_read"},
            # v0.7: a child losing a parent or guardian grieves whatever their warmth said (a parent is a parent), and hardest
            m("pf_gr_kin = 0"),
            {"if": {"and": [{"u_has_trait": "PF_CHILD"}, {"or": [{"compare_string": [{"u_val": "pf_mom"}, g("pf_dead_uid")]}, {"compare_string": [{"u_val": "pf_dad"}, g("pf_dead_uid")]},
                                                               {"compare_string": [{"u_val": "pf_guardian"}, g("pf_dead_uid")]}]}]},
             "then": [m("pf_gr_kin = 1")]},
            # full run: a band's child died a few tiles from two adults of the band, and nobody grieved (no warmth between band
            # members yet).  Losing one of your own band counts, warmth or not.
            m("pf_gr_band = (pf_dead_band > 0) * (value_or(u_pf_band, 0) == pf_dead_band)"),
            {"if": m("(pf_read_w >= 10) + pf_gr_kin + pf_gr_band > 0"), "then": [
                m("pf_mv_role = 1"), m("pf_m_str_in = pf_gr_kin == 1 ? 95 : min(95, max(pf_gr_band * 70, 50 + pf_read_w / 2))"),
                {"run_eocs": "PF_MV_lost_companion"},
                {"run_eocs": "PF_HEART_grief"},
                m("pf_grief_total = value_or(pf_grief_total, 0) + 1"),
                # day 151: "Marylin Whitmore stops beside Consuela 'Golly' Whitmore and doesn't move for a long moment." (a newborn)
                {"if": {"and": [m("pf_grief_local == 1"), m("pf_grief_shown == 0"), m("(pf_read_w >= 25) + pf_gr_kin + pf_gr_band > 0"), {"not": {"u_has_effect": "PF_infant"}}]}, "then": [
                    m("pf_grief_shown = 1"), name_into("pf_say_a"),
                    {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "grief"}}]}]}]},
    ], "u = someone who may have known the dead (pf_dead_uid).  Once per death: if they cared (warmth 10+), they keep a lost_companion memory, stronger the closer they were.  The first close one nearby is seen grieving.",
        condition={"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_dead_uid")]}}),
    eoc("PF_GRIEF_recall_i", [
        {"set_string_var": "pf_fire_c_<global_val:pf_fi>", "target_var": ctx("ri"), "parse_tags": True},
        {"run_eocs": "PF_GRIEF_recall_try", "alpha_talker": {"var_val": "ri"}},
        m("pf_fi += 1"),
    ]),
    eoc("PF_GRIEF_recall_try", [
        m("pf_ri = 0"), m("pf_rbest = -1"), m("pf_rbest_str = 0"),
        {"run_eocs": "PF_GRIEF_scan_i", "condition": m("pf_ri < 8"), "iterations": 9},
        {"if": m("pf_rbest >= 0"), "then": [
            {"set_string_var": "u_pf_mem_<global_val:pf_rbest>_rc", "target_var": ctx("mr"), "parse_tags": True},
            {"set_string_var": "u_pf_mem_<global_val:pf_rbest>_with", "target_var": ctx("mw"), "parse_tags": True},
            m("v_mr = 1"), m("pf_fire_mourned = 1"),
            {"copy_var": {"var_val": "mw"}, "target_var": g("pf_tmp_with")},
            {"set_string_var": "pf_name_<global_val:pf_tmp_with>", "target_var": ctx("nref"), "parse_tags": True},
            {"copy_var": {"var_val": "nref"}, "target_var": g("pf_say_b")},
            name_into("pf_say_a"),
            {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "mourn"}}]},
    ], "u = someone at the fire.  If they lost someone and haven't spoken of it yet, they do now (once per loss)."),
    eoc("PF_GRIEF_scan_i", [
        {"set_string_var": "u_pf_mem_<global_val:pf_ri>_kind", "target_var": ctx("mk"), "parse_tags": True},
        {"set_string_var": "u_pf_mem_<global_val:pf_ri>_str", "target_var": ctx("ms"), "parse_tags": True},
        {"set_string_var": "u_pf_mem_<global_val:pf_ri>_rc", "target_var": ctx("mr"), "parse_tags": True},
        {"if": {"and": [{"compare_string": [{"var_val": "mk"}, "lost_companion"]},
                        m("value_or(v_ms, 0) > pf_rbest_str"), m("value_or(v_mr, 0) == 0")]},
         "then": [m("pf_rbest = pf_ri"), m("pf_rbest_str = v_ms")]},
        m("pf_ri += 1"),
    ]),
]

# ============================================================ WASTE  (story 5 via a real signal: quick or dismember butchery)
files["waste.json"] = [
    eoc("PF_WASTE_on_butcher", [
        m("pf_waste_last = time('now')"),
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_waste_uid")},
        {"u_set_talker": g("pf_waste_who")},
        m("pf_waste_done = 0"),
        {"u_run_npc_eocs": ["PF_WASTE_witness"], "local": True, "npc_range": 10, "npc_must_see": True},
    ], "Bottom-up signal for story 5 (no 'burned food' event exists): someone butchers a corpse the quick or dismember way, wasting meat, in front of someone who hates waste.",
        condition={"and": ["has_alpha", {"compare_string": [ctx("butcher_type"), "ACT_BUTCHER", "ACT_DISMEMBER"]}, cooldown_ok_c("pf_waste_last", "1 h")]},
        eoc_type="EVENT", required_event="character_butchered_corpse"),
    eoc("PF_WASTE_witness", [
        {"run_eocs": "PF_ID_ensure"},
        {"if": {"and": [{"u_has_trait": "PF_Q_HATES_WASTE"}, m("pf_waste_done == 0"),
                        {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_waste_uid")]}}]},
         "then": [m("pf_waste_done = 1"), name_into("pf_say_a"),
                  {"run_eocs": "PF_SAY", "alpha_talker": "avatar", "variables": {"line": "waste"}},
                  {"run_eocs": "PF_MK_wasted_food", "alpha_talker": g("pf_waste_who"), "beta_talker": "u"}]},
    ]),
]

# ============================================================ LINES  (one place for all spoken text; u = avatar, names in pf_say_a / pf_say_b)
LINES = {
    "care":        ("<global_val:pf_say_a> comes over with a steaming mug.  \"Here.  You're soaked through.  Drink this.\"", "good"),
    "care_cold":   ("<global_val:pf_say_a> comes over with a steaming mug.  \"You're shivering.  Here, hold this.\"", "good"),
    "care_loner":  ("When you look up, there's a mug of hot tea by your pack.  <global_val:pf_say_a> is already walking away.", "good"),
    "watch_take":  ("<global_val:pf_say_a>: \"Get some sleep.  I'll take the watch.\"", "info"),
    "watch_done":  ("<global_val:pf_say_a> kept watch through the night.", "good"),
    "watch_done_day": ("<global_val:pf_say_a> kept watch while you slept.", "good"),
    "watch_short": ("<global_val:pf_say_a> kept an eye out while you slept.", "info"),
    "bicker":      ("<global_val:pf_say_a> and <global_val:pf_say_b> bicker by the fire over nothing in particular.", "info",
                    "<global_val:pf_say_a> and <global_val:pf_say_b> bicker across the table over nothing in particular."),
    "wounds":      ("<global_val:pf_say_a> kneels beside you with a rag and some clean water.  \"Hold still.  This is going to sting.\"", "good"),
    "watch_bandaged": ("You wake up bandaged.  <global_val:pf_say_a> sat up with you all night.", "good"),
    "court_you":   ("<global_val:pf_say_a> sits with you, shoulder to shoulder, and for a while neither of you says anything.", "good"),
    "court_npc":   ("<global_val:pf_say_a> and <global_val:pf_say_b> sit a little apart from the others, talking quietly.", "info"),
    "smitten_you": ("<global_val:pf_say_a> sits next to you tonight, closer than they need to.", "info"),
    "smitten":     ("<global_val:pf_say_a> keeps glancing at <global_val:pf_say_b> across the fire.", "info",
                    "<global_val:pf_say_a> keeps glancing at <global_val:pf_say_b> across the room."),
    "confess_yes": ("<global_val:pf_say_a> says something to <global_val:pf_say_b>, too quietly to hear.  <global_val:pf_say_b> takes their hand.", "good"),
    "confess_no_npc": ("<global_val:pf_say_a> says something to <global_val:pf_say_b>, too quietly to hear.  <global_val:pf_say_b> shakes their head, gently.  <global_val:pf_say_a> stares into the fire for the rest of the night.", "bad",
                    "<global_val:pf_say_a> says something to <global_val:pf_say_b>, too quietly to hear.  <global_val:pf_say_b> shakes their head, gently.  <global_val:pf_say_a> goes to bed early."),
    "grief":       ("<global_val:pf_say_a> stops beside <global_val:pf_dead_name> and doesn't move for a long moment.", "bad"),
    "mourn":       ("<global_val:pf_say_a> stares into the fire.  \"<global_val:pf_say_b> would have liked this.\"", "info",
                    "<global_val:pf_say_a> looks at the empty chair.  \"<global_val:pf_say_b> would have liked this.\""),
    "keepsake":    ("On the way past, <global_val:pf_say_a> drops something in your lap: a little carved animal, still rough from the knife.  \"Here.  Made it for you.\"", "good"),
    "keepsake_1":  ("<global_val:pf_say_a> blows the shavings off a little carving, turns it over once, and hands it to you without a word.", "good"),
    "keepsake_2":  ("<global_val:pf_say_a> has been whittling all evening.  At the end of it, they set the little figure on your knee.  \"It's meant to be you.  Don't laugh.\"", "good"),
    "waste":       ("<global_val:pf_say_a> watches the hack job and winces.  \"You're wasting half of it.\"", "bad"),
    "tease":       ("<global_val:pf_say_a> grins at <global_val:pf_say_b>.  \"Better out than in, huh?\"", "info"),
}
say_eff = []
for key, v in LINES.items():
    say_eff.append({"if": {"compare_string": [ctx("line"), key]}, "then": [hsay(v[0], v[2], v[1]) if len(v) > 2 else say(v[0], v[1])]})
ACTS = {
    "act_story":   "<global_val:pf_say_a> tells a long story about a road trip before all this, and gets half the fire laughing.",
    "act_whittle": "<global_val:pf_say_a> sits at the edge of the light, whittling something small.",
    "act_cook":    "<global_val:pf_say_a> fusses over a pot on the coals and makes sure everyone gets some.",
    "act_joke":    "<global_val:pf_say_a> cracks a joke about the dead that's in very poor taste.  Somebody snorts anyway.",
    "act_proud":   "<global_val:pf_say_a> talks about the time they held a door against a dozen of them.  It gets bigger every telling.",
    "act_child":   "<global_val:pf_say_a> sits close to the fire, hugging their knees, and listens.",
    "act_quiet":   "<global_val:pf_say_a> stares into the flames, quiet.",
    "act_mourn":   "<global_val:pf_say_a> sits at the edge of the light, not really listening.",
}
ACTS_HOME = {
    "act_story":   "<global_val:pf_say_a> tells a long story about a road trip before all this, and gets half the room laughing.",
    "act_whittle": "<global_val:pf_say_a> sits by the window, whittling something small.",
    "act_cook":    "<global_val:pf_say_a> fusses in the kitchen and makes sure everyone gets a bowl.",
    "act_child":   "<global_val:pf_say_a> sits on the floor, hugging their knees, and listens.",
    "act_quiet":   "<global_val:pf_say_a> sits in the corner, quiet, looking out at the dark.",
    "act_mourn":   "<global_val:pf_say_a> sits apart from the others, not really listening.",
}
ACTS.update({  # props and instruments (v0.4): chosen by PF_HOME_prop_act
    "act_guitar":  "<global_val:pf_say_a> tunes up a battered guitar and plays something everyone almost remembers.",
    "act_violin":  "<global_val:pf_say_a> plays the violin, badly at first, then not badly at all.",
    "act_cards":   "<global_val:pf_say_a> deals a hand of cards and loses on purpose to whoever looks like they need a win.",
    "act_read":    "<global_val:pf_say_a> finds a paperback on the shelf and reads it aloud, doing all the voices.",
    "act_piano":   "<global_val:pf_say_a> sits down at the piano.  Half the keys stick, and it's still the best thing anyone has heard in weeks.",
    "act_couch":   "<global_val:pf_say_a> sinks into the couch with a sigh and is asleep within minutes.",
})
# Variety pass (2026-10-11): alternatives per act, (fire text, home text); one is picked at random, never the same twice running.
ACT_ALT = {
    "act_story": [("<global_val:pf_say_a> tells the one about the wedding where the cake fell over, and everyone pretends they haven't heard it before.",
                   "<global_val:pf_say_a> tells the one about the wedding where the cake fell over, and everyone pretends they haven't heard it before."),
                  ("<global_val:pf_say_a> does impressions of people from before: a boss, a neighbor, a TV chef.  The chef gets the biggest laugh.",
                   "<global_val:pf_say_a> does impressions of people from before: a boss, a neighbor, a TV chef.  The chef gets the biggest laugh.")],
    "act_whittle": [("<global_val:pf_say_a> works a stick into a spoon, shaving by shaving.", "<global_val:pf_say_a> works a stick into a spoon at the table, shaving by shaving."),
                    ("<global_val:pf_say_a> braids a length of cord into something that might be a bracelet.", "<global_val:pf_say_a> braids a length of cord into something that might be a bracelet.")],
    "act_cook": [("<global_val:pf_say_a> roasts something on a stick and hands it round, burnt on one side and raw on the other.  Nobody complains.",
                  "<global_val:pf_say_a> heats up whatever's left and hands round bowls.  Nobody complains.")],
    "act_joke": [("<global_val:pf_say_a> does a bit about a zombie trying to use a revolving door.  It goes on too long and gets funnier for it.",
                  "<global_val:pf_say_a> does a bit about a zombie trying to use a revolving door.  It goes on too long and gets funnier for it."),
                 ("<global_val:pf_say_a> proposes a toast to the dead, \"who never complain about the cooking.\"",
                  "<global_val:pf_say_a> proposes a toast to the dead, \"who never complain about the cooking.\"")],
    "act_proud": [("<global_val:pf_say_a> explains, at length, the right way to sharpen a machete.  Nobody asked.",
                   "<global_val:pf_say_a> explains, at length, the right way to sharpen a machete.  Nobody asked.")],
    "act_child": [("<global_val:pf_say_a> falls asleep against the nearest grown-up halfway through a story.", "<global_val:pf_say_a> falls asleep against the nearest grown-up halfway through a story."),
                  ("<global_val:pf_say_a> asks for the scary story, then hides their face for the scary part.", "<global_val:pf_say_a> asks for the scary story, then hides their face for the scary part.")],
    "act_quiet": [("<global_val:pf_say_a> turns a ring over and over in their fingers, watching the fire.", "<global_val:pf_say_a> turns a ring over and over in their fingers, watching the window."),
                  ("<global_val:pf_say_a> listens to everyone else and smiles at the right places.", "<global_val:pf_say_a> listens to everyone else and smiles at the right places.")],
}
ACT_MORE = {
    'act_story': [
        ('%(A)s tells about the worst job they ever had, and it turns into a contest.  Nobody beats the one about the septic tank.', '%(A)s tells about the worst job they ever had, and it turns into a contest.  Nobody beats the one about the septic tank.'),
        ('%(A)s describes, course by course, the best meal they ever ate.  By dessert people are groaning.', '%(A)s describes, course by course, the best meal they ever ate.  By dessert people are groaning.'),
        ("%(A)s tells a ghost story.  It's not very good, but the timing is, and someone yelps.", "%(A)s tells a ghost story.  It's not very good, but the timing is, and someone yelps."),
    ],
    'act_whittle': [
        ('%(A)s sews a patch onto a jacket, biting the thread off at the end.', '%(A)s sews a patch onto a jacket, biting the thread off at the end.'),
        ('%(A)s takes a broken flashlight apart and puts it back together, and it works.  They look surprised.', '%(A)s takes a broken flashlight apart and puts it back together, and it works.  They look surprised.'),
    ],
    'act_cook': [
        ("%(A)s makes tea out of something they found growing by the road.  It's terrible.  Everyone drinks it.", "%(A)s makes tea out of something they found growing by the road.  It's terrible.  Everyone drinks it."),
        ("%(A)s divides a chocolate bar into exactly equal squares, and won't hear any argument about it.", "%(A)s divides a chocolate bar into exactly equal squares, and won't hear any argument about it."),
    ],
    'act_joke': [
        ("%(A)s keeps a running list of the stupidest ways they've nearly died, and adds today's to it out loud.", "%(A)s keeps a running list of the stupidest ways they've nearly died, and adds today's to it out loud."),
        ('%(A)s does a weather report for the end of the world.  "Scattered dead, clearing by evening."', '%(A)s does a weather report for the end of the world.  "Scattered dead, clearing by evening."'),
    ],
    'act_proud': [
        ('%(A)s shows off a scar and the story that goes with it.  The story has more teeth every time.', '%(A)s shows off a scar and the story that goes with it.  The story has more teeth every time.'),
        ('%(A)s explains how they would have handled today, if anyone had asked.', '%(A)s explains how they would have handled today, if anyone had asked.'),
        ('%(A)s cleans their weapon slowly where everyone can see it, and waits to be asked about it.', '%(A)s cleans their weapon slowly where everyone can see it, and waits to be asked about it.'),
    ],
    'act_quiet': [
        ('%(A)s writes in a notebook by the light, and closes it when anyone looks over.', '%(A)s writes in a notebook by the lamp, and closes it when anyone looks over.'),
        ("%(A)s hums something under their breath and doesn't notice the others have gone quiet to listen.", "%(A)s hums something under their breath and doesn't notice the others have gone quiet to listen."),
    ],
    'act_child': [
        ('%(A)s wants to know what the stars are called.  Nobody really knows, so they make names up together.', "%(A)s wants to know what everyone's favorite animal was, before.  It takes all evening."),
        # full run days 128 and 130: two lines alternated, so the same one came back every other evening
        ('%(A)s teaches everyone a clapping game from school.  The grown-ups are terrible at it.', '%(A)s teaches everyone a clapping game from school.  The grown-ups are terrible at it.'),
        ('%(A)s draws in the dirt with a stick: a house, a dog, a lot of people holding hands.', '%(A)s draws on the floor with a bit of charcoal: a house, a dog, a lot of people holding hands.'),
        ('%(A)s asks for the story about the time before, and listens with their whole face.', '%(A)s asks for the story about the time before, and listens with their whole face.'),
    ],
}
for _k, _v in ACT_MORE.items():
    ACT_ALT.setdefault(_k, []).extend(_v)
act_eff = []
for k, v in ACTS.items():
    opts = [(v, ACTS_HOME.get(k))] + [(f % {"A": "<global_val:pf_say_a>"}, h % {"A": "<global_val:pf_say_a>"}) for f, h in ACT_ALT.get(k, [])]
    if len(opts) == 1:
        act_eff.append({"if": {"compare_string": [g("pf_act"), k]}, "then": [hsay(v, ACTS_HOME[k]) if k in ACTS_HOME else say(v)]})
        continue
    n = len(opts)
    # full run day 138: Lakia and Lizeth both "asked for the story about the time before" at one camp evening; only
    # back-to-back repeats were avoided.  Each evening keeps a mask of the lines it has used (seeded with yesterday's last).
    mask, day = f"pf_actm_{k}", f"pf_actd_{k}"
    used = " + ".join(f"(_p == {i}) * (floor({mask} / {1 << i}) % 2)" for i in range(n))
    bit = " + ".join(f"(_p == {i}) * {1 << i}" for i in range(n))
    branch = [{"if": m(f"value_or({day}, -1) != floor(time('now') / time('1 d'))"), "then": [
                  m(f"{day} = floor(time('now') / time('1 d'))"),
                  m(f"{mask} = " + " + ".join(f"(value_or(pf_actv_{k}, -1) == {i}) * {1 << i}" for i in range(n)))]},
              m(f"_p = rand({n - 1})")]
    branch += [{"if": m(f"{used} > 0"), "then": [m(f"_p = (_p + 1) % {n}")]} for _ in range(n - 1)]
    branch += [{"if": m(f"{used} == 0"), "then": [m(f"{mask} += {bit}")]}, m(f"pf_actv_{k} = _p")]
    branch += [{"if": m(f"_p == {i}"), "then": [hsay(f, h) if h else say(f)]} for i, (f, h) in enumerate(opts)]
    act_eff.append({"if": {"compare_string": [g("pf_act"), k]}, "then": branch})
SAVE_LINES = [  # (case, debt condition, text)  case 1 = an NPC saved you, 2 = you saved an NPC, 3 = NPC saved NPC.  pf_save_d = how many the saved one owes the saver now.
    (1, "pf_save_d == 1", "<global_val:pf_say_a> drags the thing off you and finishes it.  \"Got you.  You're okay.  You're okay.\""),
    (1, "pf_save_d >= 2", "<global_val:pf_say_a> drags the thing off you and finishes it.  \"That's <global_val:pf_save_n> times now.  Stop making me do this.\""),
    (1, "pf_save_d == 0", "<global_val:pf_say_a> drags the thing off you and finishes it.  \"There.  Now we're even.\""),
    (1, "pf_save_d < 0",  "<global_val:pf_say_a> drags the thing off you and finishes it.  \"Still owe you <global_val:pf_save_n>.  I'm catching up.\""),
    (2, "pf_save_d == 1", "<global_val:pf_say_b> stares at the thing you just put down, then at you.  \"I thought that was it.  I owe you one.\""),
    (2, "pf_save_d >= 2", "<global_val:pf_say_b> stares at the thing you just put down, then at you.  \"That's <global_val:pf_save_n> I owe you now.\""),
    (2, "pf_save_d == 0", "<global_val:pf_say_b> lets out a shaky breath.  \"Guess we're square.\""),
    (2, "pf_save_d < 0",  "<global_val:pf_say_b> lets out a shaky breath.  \"Okay.  Now you only owe me <global_val:pf_save_n>.\""),
    (3, "pf_save_d >= 2", "<global_val:pf_say_a> drags the thing off <global_val:pf_say_b> again."),
    (3, "pf_save_d < 2",  "<global_val:pf_say_a> drags the thing off <global_val:pf_say_b> and finishes it."),
]
save_eff = [{"if": {"and": [m(f"pf_save_case == {c}"), m(cond)]}, "then": [say(t, "good")]} for c, cond, t in SAVE_LINES]
files["lines.json"] = [eoc("PF_SAY", say_eff, "u = avatar.  All spoken lines, picked by the context var 'line'.  Names come from pf_say_a / pf_say_b."),
                       eoc("PF_SAY_act", act_eff, "u = avatar.  Fire activity lines, picked by pf_act."),
                       eoc("PF_SAY_save", save_eff, "u = avatar.  Rescue lines: who saved whom, and the running score between them.")]

# ============================================================ KEEPSAKES  (things people make for you: a memory you can hold)
files["keepsake.json"] = [{
    "type": "ITEM", "id": "PF_carved_keepsake", "name": {"str": "carved keepsake"},
    "description": "A little figure whittled from scrap wood by firelight.  Someone made this for you.",
    "category": "other", "material": ["wood"], "weight": "30 g", "volume": "50 ml",
    "price": "1 cent", "price_postapoc": "1 cent", "symbol": "f", "color": "brown",
    "variant_type": "generic",
    "variants": [
        {"id": "PF_keepsake_fox", "name": {"str": "carved fox", "str_pl": "carved foxes"}, "description": "A little fox whittled from scrap wood by firelight, its tail curled around its feet.  Someone made this for you."},
        {"id": "PF_keepsake_bird", "name": {"str": "carved bird"}, "description": "A little bird whittled from scrap wood by firelight, wings folded, head cocked as if listening.  Someone made this for you."},
        {"id": "PF_keepsake_bear", "name": {"str": "carved bear"}, "description": "A stubby little bear whittled from scrap wood by firelight.  The knife slipped on one ear.  Someone made this for you."},
        {"id": "PF_keepsake_dog", "name": {"str": "carved dog"}, "description": "A little sitting dog whittled from scrap wood by firelight, the way dogs used to wait by the door.  Someone made this for you."},
    ]}]

# context vars set inside a called EOC don't come back to the caller, so view names are always inlined
VNAMES = [{"set_string_var": f"u_pf_v_<global_val:pf_m_other>_{suf}", "target_var": ctx(c), "parse_tags": True}
          for c, suf in (("rw", "w"), ("rt", "t"), ("rx", "x"), ("rpw", "pw"), ("rpt", "pt"), ("rl", "l"), ("ra", "a"), ("rpa", "pa"), ("rc", "c"), ("rf", "f"))]
# ============================================================ LIFE LAB  (manual triggers for testing each system)
LAB = [
    ("PF_LL_care", "Care: I'm cold (care check now)", "Gives you the cold effect and runs the care check immediately.",
     [{"u_add_effect": "cold", "duration": "30 minutes"}, m("pf_care_last = -1"), {"run_eocs": "PF_CARE_check"}]),
    ("PF_LL_fire", "Fire: light a campfire 3 tiles east", "Builds a fire ring 3 tiles east of you, clears the grass around it, and lights it.",
     [{"u_location_variable": g("pf_ll_fire"), "x_adjust": 3},
      {"u_transform_radius": 2, "ter_furn_transform": "PF_LL_clear_grass", "target_var": g("pf_ll_fire")},
      {"u_transform_radius": 0, "ter_furn_transform": "PF_LL_firering", "target_var": g("pf_ll_fire")},
      {"map_spawn_item": "log", "loc": g("pf_ll_fire"), "count": 3},
      {"u_set_field": "fd_fire", "radius": 0, "intensity": 2, "age": "0 seconds", "hit_player": False, "target_var": g("pf_ll_fire")},
      say("[lab] A campfire crackles to life.")]),
    ("PF_LL_gather", "Fire: start tonight's evening now (ignores the clock)", "Resets tonight's evening and advances it once: people sit down if it's calm.",
     [m("pf_eve_day = floor(time('now') / time('1 d'))"), m("pf_eve_state = 0"), m("pf_eve_done_day = -1"), m("pf_eve_fought = 0"),
      {"u_location_variable": g("pf_fire_loc"), "field": "fd_fire", "target_max_radius": 15,
       "true_eocs": ["PF_FIRE_step"],
       "false_eocs": [{"id": "PF_LL_nofire", "effect": [say("[lab] No fire within 15 tiles.")]}]}]),
    ("PF_LL_step", "Fire: advance the evening one tick (as if 20 minutes passed)", "One evening tick: scatter if there's trouble, sit back down if it's calm again, or run the evening if people have been seated long enough.",
     [m("pf_eve_seat_t = time('now') - time('20 m')"),
      {"u_location_variable": g("pf_fire_loc"), "field": "fd_fire", "target_max_radius": 15,
       "true_eocs": ["PF_FIRE_step"], "false_eocs": ["PF_LL_nofire"]},
      {"run_eocs": "PF_THREAT_scan"}, say("[lab] Evening state <global_val:pf_eve_state>, threat <global_val:pf_threat>.")]),
    ("PF_LL_sleep", "Watch: I fall asleep", "Runs the falling-asleep signal (someone takes the watch).", [{"run_eocs": "PF_WATCH_on_sleep"}]),
    ("PF_LL_wake", "Watch: I wake up", "Runs the waking signal (the watcher's night counts).", [{"run_eocs": "PF_WATCH_on_wake"}]),
    ("PF_LL_gallows", "Friction: give everyone within 10 tiles gallows humor", "So the tease test has a teaser.",
     [{"u_run_npc_eocs": [{"id": "PF_LL_gallows_one", "effect": [{"run_eocs": "PF_ID_ensure"}, {"u_add_trait": "PF_Q_GALLOWS"}]}], "local": True, "npc_range": 10},
      say("[lab] Everyone nearby now has gallows humor.")]),
    ("PF_LL_throwup", "Friction: I throw up", "Runs the throw-up signal for you (someone with gallows humor teases you).", [m("pf_tease_last = -1"), {"run_eocs": "PF_TEASE_on_throwup"}]),
    ("PF_LL_neardeath", "Witness: I nearly die (in front of everyone)", "Reports a near_death moment of strength 70; everyone who can see you remembers it.",
     [m("pf_m_str_in = 70"), {"run_eocs": "PF_MK_near_death"}, say("[lab] You stagger, nearly going down.  People saw.")]),
    ("PF_LL_hurt", "Wounds: I'm bitten and bleeding (tend check now)", "Bites and bleeds you a little, then runs the wound check (needs no hostiles within 15 tiles).",
     [{"u_add_effect": "bite", "duration": "1 hours", "target_part": "torso"}, {"u_add_effect": "bleed", "duration": "10 minutes", "target_part": "torso"},
      m("u_hp('torso') = u_hp_max('torso') * 0.7"), m("pf_wound_last = -1"), {"run_eocs": "PF_WOUND_tick"}]),
    ("PF_LL_beat", "Fire: run the evening beat now", "Runs the evening itself immediately (no threat check).", [{"run_eocs": "PF_FIRE_beat"}]),
    ("PF_LL_keep", "Fire: the next activity is a carving with a keepsake", "The first person to do something at the next evening whittles, and the carving is for you.", [m("pf_keep_force = 1"), say("[lab] Someone will carve you something tonight.")]),
    ("PF_LL_waste", "Waste: I quick-butcher a corpse (signal)", "Runs the butchery signal as if you quick-butchered something.  Needs someone who hates waste nearby.",
     [m("pf_waste_last = -1"), {"run_eocs": "PF_WASTE_on_butcher", "variables": {"butcher_type": "ACT_BUTCHER"}}]),
    ("PF_LL_hateswaste", "Waste: give everyone within 10 tiles 'hates waste'", "So the waste test has a witness.",
     [{"u_run_npc_eocs": [{"id": "PF_LL_hw_one", "effect": [{"run_eocs": "PF_ID_ensure"}, {"u_add_trait": "PF_Q_HATES_WASTE"}]}], "local": True, "npc_range": 10},
      say("[lab] Everyone nearby now hates waste.")]),
    ("PF_LL_kill_npc", "Combat: the nearest person kills the thing on me", "You're hurt; the nearest NPC (within 5 tiles) kills something next to you.  Tests shared danger and being saved (with the running score).",
     [m("u_hp('torso') = min(u_hp('torso'), u_hp_max('torso') * 0.55)"), m("u_pf_saved_last = -1"),
      {"u_location_variable": g("pf_ll_vpos")}, {"run_eocs": "PF_LL_nearest"},
      {"if": m("pf_ll_kd < 99"),
       "then": [{"run_eocs": "PF_LL_kill_one", "alpha_talker": g("pf_ll_kwho")}],
       "else": [say("[lab] Nobody within 5 tiles.")]}]),
    ("PF_LL_save_npc", "Combat: I kill the thing on the nearest person", "The nearest NPC (within 5 tiles) is hurt and you kill something next to them.  Tests you saving them, and the running score.",
     [{"u_location_variable": g("pf_ll_kav")}, {"run_eocs": "PF_LL_nearest"},
      {"if": m("pf_ll_kd < 99"),
       "then": [{"run_eocs": "PF_LL_hurt_one", "alpha_talker": g("pf_ll_kwho")}, m("u_pf_kill_last = -1"),
                {"run_eocs": "PF_COMBAT_kill", "variables": {"lab_victim": "set"}}],
       "else": [say("[lab] Nobody within 5 tiles.")]}]),
    ("PF_LL_nearest", None, None,
     [m("pf_ll_kd = 99"), {"u_location_variable": g("pf_ll_kav")},
      {"u_run_npc_eocs": [{"id": "PF_LL_kill_near", "effect": [
          {"u_location_variable": {"u_val": "pf_pos"}},
          {"if": m("distance(u_pf_pos, pf_ll_kav) < pf_ll_kd"),
           "then": [m("pf_ll_kd = distance(u_pf_pos, pf_ll_kav)"), {"u_set_talker": g("pf_ll_kwho")}]}]}], "local": True, "npc_range": 5}]),
    ("PF_LL_hurt_one", None, None,
     [m("u_hp('torso') = min(u_hp('torso'), u_hp_max('torso') * 0.5)"), m("u_pf_saved_last = -1"), {"u_location_variable": g("pf_ll_vpos")}]),
    ("PF_LL_kill_one", None, None, [m("u_pf_kill_last = -1"), {"run_eocs": "PF_COMBAT_kill", "variables": {"lab_victim": "set"}}]),
    ("PF_LL_kill_me", "Combat: I kill something", "Runs the kill signal with you as the killer.  Everyone within 8 tiles shares the danger.",
     [m("u_pf_kill_last = -1"), {"run_eocs": "PF_COMBAT_kill"}, say("[lab] You put the thing down.")]),
    ("PF_LL_bandeve", "Social: every band spends 10 evenings together (off-screen camp)", "Runs the off-screen band evening 10 times for every band in the roster, wherever it is, ignoring the clock.  Then check a band member's views in the People menu.",
     [m("pf_ll_rep = 0"),
      {"run_eocs": "PF_LL_bandeve_all", "condition": m("pf_ll_rep < 10"), "iterations": 11},
      say("[lab] <global_val:pf_social_evenings_total> band evenings so far.")]),
    ("PF_LL_bandeve_all", None, None,
     [m("pf_band_i = 0"), {"run_eocs": "PF_LL_bandeve_one", "condition": m("pf_band_i < pf_band_n"), "iterations": 1000}, m("pf_ll_rep += 1")]),
    ("PF_LL_bandeve_one", None, None,
     [{"set_string_var": "pf_slot_<global_val:pf_band_i>", "target_var": ctx("ref"), "parse_tags": True},
      {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}},
       "then": [{"u_run_npc_eocs": ["PF_SOCIAL_band_evening"], "unique_ids": [{"var_val": "ref"}], "local": False}]},
      m("pf_band_i += 1")]),
    ("PF_LL_grief", "Social: the nearest band member (not a leader, not a child) dies", "Kills the nearest adult A-Life band member within 10 tiles, so you can see who grieves and hear them speak of it at the fire.",
     [m("pf_ll_kd = 99"), {"u_location_variable": g("pf_ll_kav")},
      {"u_run_npc_eocs": [{"id": "PF_LL_grief_near", "condition": {"and": [{"u_has_trait": "PF_AGENT"}, {"not": {"u_has_trait": "PF_CHILD"}}, m("value_or(u_pf_is_leader, 0) == 0"),
                                                         # 2026-10-16 (KinfoldLab): it took Lakia, a grown resident.  Band members only.
                                                         m("value_or(u_pf_band, 0) > 0"), m("value_or(u_pf_resident, 0) == 0")]},
                           "effect": [{"u_location_variable": {"u_val": "pf_pos"}},
                                      {"if": m("distance(u_pf_pos, pf_ll_kav) < pf_ll_kd"),
                                       "then": [m("pf_ll_kd = distance(u_pf_pos, pf_ll_kav)"), {"u_set_talker": g("pf_ll_kwho")}]}]}], "local": True, "npc_range": 10},
      {"if": m("pf_ll_kd < 99"),
       "then": [{"run_eocs": {"id": "PF_LL_grief_die", "effect": ["u_die"]}, "alpha_talker": g("pf_ll_kwho")}, say("[lab] Someone is gone.  Grieving: <global_val:pf_grief_total> so far.")],
       "else": [say("[lab] No adult band member within 10 tiles.")]}]),
    ("PF_LL_fall", "Romance: the nearest person falls for you (attraction 65)", "Sets the nearest NPC's attraction and warmth toward you high enough to confess at the next fire, if their nature allows it.  Shows their romantic nature.",
     [{"u_location_variable": g("pf_ll_kav")}, {"run_eocs": "PF_LL_nearest"},
      {"if": m("pf_ll_kd < 99"), "then": [{"run_eocs": "PF_LL_fall_one", "alpha_talker": g("pf_ll_kwho")}, say("[lab] The nearest adult now feels strongly about you (children are never affected).")], "else": [say("[lab] Nobody within 5 tiles.")]}]),
    ("PF_LL_fall_one", None, None,
     [{"run_eocs": "PF_ID_ensure"}, {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, *VNAMES,
      m("v_ra = 65"), m("v_rpa = 65"), m("v_rw = max(v_rw, 40)"), m("v_rpw = max(v_rpw, 40)"), m("u_pf_conf_last = -1"), m("u_pf_awk_until = 0"),
      {"if": m("value_or(u_pf_rom, 0) == 0"), "then": [m("u_pf_rom = 1"), m("u_pf_orient = 2")]},
      {"if": {"u_has_trait": "PF_CHILD"}, "then": [say("[lab] That's a child.  Romance never applies to children.")],
       "else": [say("[lab] <u_name> now feels strongly about you (and was made romantic and drawn to everyone, for the test).")]}]),
    ("PF_LL_couple", "Romance: two nearby adults fall for each other", "The two nearest adult NPCs within 10 tiles get attraction 65 and warmth 40 toward each other, so one may confess at the next fire.",
     [m("pf_ll_cn = 0"),
      {"u_run_npc_eocs": [{"id": "PF_LL_couple_pick", "condition": {"and": [m("pf_ll_cn < 2"), {"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18"), m("value_or(u_pf_has_sweet, 0) == 0")]},
                           "effect": [{"run_eocs": "PF_ID_ensure"},
                                      {"set_string_var": "pf_ll_c_<global_val:pf_ll_cn>", "target_var": ctx("cref"), "parse_tags": True},
                                      {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "cref"}},
                                      m("pf_ll_cn += 1")]}], "local": True, "npc_range": 10},
      {"if": m("pf_ll_cn == 2"),
       "then": [{"u_run_npc_eocs": ["PF_LL_couple_set"], "local": True, "npc_range": 10}, say("[lab] Two people are falling for each other.")],
       "else": [say("[lab] Need two adults within 10 tiles.")]}]),
    ("PF_LL_couple_set", None, None,
     [{"if": {"compare_string": [{"u_val": "pf_uid"}, g("pf_ll_c_0")]}, "then": [{"copy_var": g("pf_ll_c_1"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_LL_couple_view"}]},
      {"if": {"compare_string": [{"u_val": "pf_uid"}, g("pf_ll_c_1")]}, "then": [{"copy_var": g("pf_ll_c_0"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_LL_couple_view"}]}]),
    ("PF_LL_couple_view", None, None,
     [*VNAMES, {"if": m("value_or(v_rl, -1) < 0"), "then": [m("v_rl = time('now')"), m("v_rt = 0"), m("v_rx = 0"), m("v_rpt = 0"), m("v_rc = 0.5"), m("v_rf = 1")]},
      m("v_ra = 65"), m("v_rpa = 65"), m("v_rw = max(value_or(v_rw, 0), 40)"), m("v_rpw = max(value_or(v_rpw, 0), 40)"),
      m("u_pf_rom = 1"), m("u_pf_orient = 2"), m("u_pf_conf_last = -1"), m("u_pf_awk_until = 0")]),
    ("PF_LL_stats", "Stats: what has happened so far", "Counters from the whole run: moments, memories, off-screen band camps and hunts, couples, rejections, grief.",
     [m("pf_st_a = value_or(pf_moments_total, 0)"), m("pf_st_b = value_or(pf_memories_total, 0)"), m("pf_st_c = value_or(pf_social_evenings_total, 0)"),
      m("pf_st_d = value_or(pf_social_hunts_total, 0)"), m("pf_st_e = value_or(pf_couples_total, 0)"), m("pf_st_f = value_or(pf_rejections_total, 0)"),
      m("pf_st_g = value_or(pf_grief_total, 0)"), m("pf_st_h = value_or(pf_eve_state, 0)"),
      say("[stats] moments <global_val:pf_st_a>, memories kept <global_val:pf_st_b>, band camps <global_val:pf_st_c>, band hunts <global_val:pf_st_d>, couples <global_val:pf_st_e>, rejections <global_val:pf_st_f>, grieving <global_val:pf_st_g>, tonight's evening state <global_val:pf_st_h>.")]),
    ("PF_LL_hearts", "Hearts lab (v0.2): couples, jealousy, burial", "Opens the v0.2 test menu.", [{"run_eocs": "PF_HL_open"}]),
    ("PF_LL_family", "Family lab (v0.3): pregnancy, babies, growing up, orphans", "Opens the v0.3 test menu.", [{"run_eocs": "PF_FL_open"}]),
    ("PF_LL_home", "Home lab (v0.4): evenings at home, breakfast, residents, the world", "Opens the v0.4 test menu.", [{"run_eocs": "PF_HML_open"}]),
    ("PF_LL_reset", "Reset all cooldowns", "Care, tease, meal, near-death and tonight's fire.",
     [m("pf_care_last = -1"), m("pf_tease_last = -1"), m("pf_meal_last = -1"), m("pf_neardeath_last = -1"), m("pf_eve_done_day = -1"), m("pf_eve_state = 0"),
      m("pf_wound_last = -1"), m("u_pf_saved_last = -1"), m("pf_waste_last = -1"),
      say("[lab] Cooldowns reset.")]),
]
MENU = [x for x in LAB if x[1]]
lab_objs = [eoc("PF_LL_open", [{
    "run_eoc_selector": [i for i, _, _, _ in MENU], "names": [n for _, n, _, _ in MENU], "descriptions": [d for _, _, d, _ in MENU],
    "keys": [c for c in "abcdefghijklmnopqrstuvwxyz"][:len(MENU)], "title": "Life lab (v0.1)", "allow_cancel": True}])]
lab_objs += [eoc(i, eff) for i, _, _, eff in LAB]
GRASS = ["t_grass", "t_grass_dead", "t_grass_golf", "t_grass_grazed", "t_grass_long", "t_grass_tall", "t_grass_white"]
lab_objs += [
    {"type": "ter_furn_transform", "id": "PF_LL_clear_grass", "terrain": [{"result": "t_dirt", "valid_terrain": GRASS}]},
    {"type": "ter_furn_transform", "id": "PF_LL_firering", "furniture": [{"result": "f_firering", "valid_furniture": ["f_null"]}]},
]
files["lab_life.json"] = lab_objs

os.makedirs(OUT, exist_ok=True)
# ============================================================ DAYTIME  (variety pass 2026-10-11: playtest 2 found adults idle all day)
# Every 90 minutes by day, when it's calm, up to two people near you do something small: alone (by quirk, temperament,
# weather, or a general pool) or with someone (by how they feel about each other).  Pillar 3: parallel play.
DAY_CALM = "value_or(pf_set_chatter, 1) == 1"
def pick(var, n):
    """A random index in 0..n-1 that isn't one this pool used recently: the last one for pools of 4 or fewer, else the last
    min(n // 2, 6).  Playtest 3: with only back-to-back repeats ruled out, the same idle line came round three times in a day;
    full run day 161: with the last three ruled out, a 7-line pool still repeated within four hours."""
    if n <= 4:
        return [m(f"_p = rand({n - 1})"), {"if": m(f"_p == value_or({var}, -1)"), "then": [m(f"_p = (_p + 1) % {n}")]}, m(f"{var} = _p")]
    k = min(n // 2, 6)
    hist = [var] + [f"{var}_{c}" for c in "bcdef"[:k - 1]]
    used = "(" + ") + (".join(f"_p == value_or({h}, -1)" for h in hist) + ") > 0"
    return [m(f"_p = rand({n - 1})")] + [{"if": m(used), "then": [m(f"_p = (_p + 1) % {n}")]} for _ in range(k)] + [
        m(f"{hist[i]} = value_or({hist[i - 1]}, -1)") for i in range(k - 1, 0, -1)] + [m(f"{var} = _p")]
def pool(var, key_prefix, texts):
    """Sets global pf_day_line to key_prefix + chosen index; returns the effects and the (key, text) pairs."""
    eff = pick(var, len(texts)) + [{"if": m(f"_p == {i}"), "then": [{"set_string_var": f"{key_prefix}{i}", "target_var": g("pf_day_line")}]}
                                     for i in range(len(texts))]
    return eff, [(f"{key_prefix}{i}", t) for i, t in enumerate(texts)]
A, B = "<global_val:pf_say_a>", "<global_val:pf_say_b>"
DAY_LINES = {}
SOLO = [
    f"{A} sits on an upturned bucket, sharpening a knife on a stone, slow and even.",
    f"{A} mends a sock with a needle and a lot of muttering.",
    f"{A} reads a battered paperback with the cover torn off, moving their lips a little.",
    f"{A} writes something in a notebook, then crosses it out, then writes it again.",
    f"{A} counts their ammunition, then counts it again.",
    f"{A} stands at the edge of the place for a long while, just watching the road.",
    f"{A} takes their boots off and stretches their toes in the air with a groan of pure joy.",
    f"{A} sorts a pile of scavenged screws by size, for no reason anyone can see.",
    f"{A} hums the same four bars of some song over and over, and doesn't seem to know they're doing it.",
    f"{A} naps sitting up, chin on their chest, one hand still on their weapon.",
]
solo_eff, kv = pool("pf_day_solo_last", "day_solo_", SOLO); DAY_LINES.update(kv)
WET = [
    f"{A} sits in a doorway, watching the rain come down, and doesn't say anything for an hour.",
    f"{A} sets out every pot and can they own to catch the rain, and looks very pleased with themselves.",
    f"{A} curses the rain, the mud, and the rain again.",
    f"{A} wrings out their socks for the third time today and gives up on them.",
    f"{A} stands under the eaves with their face turned up, letting the rain wash it.",
    f"{A} plays a slow game of checkers on a board scratched into the floor, listening to the rain on the roof.",
    f"{A} patches a leak with a strip of tarp and a lot of language.",
]
wet_eff, kv = pool("pf_day_wet_last", "day_wet_", WET); DAY_LINES.update(kv)
SUN = [
    f"{A} lies in the sun with their eyes closed, like a cat.",
    f"{A} hangs washing on a line strung between two posts.  Nothing has ever looked so normal.",
    f"{A} spreads damp gear out on the ground to dry, and guards it like treasure.",
    f"{A} finds a warm patch of wall and leans on it with their eyes shut.",
    f"{A} takes their shirt off to feel the sun, and gets told they're blinding everyone.",
]
sun_eff, kv = pool("pf_day_sun_last", "day_sun_", SUN); DAY_LINES.update(kv)
QUIRK = {  # trait: lines (one picked)
    "PF_T_LONER": [f"{A} wanders off alone and comes back an hour later with nothing to show for it, looking better for it."],
    "PF_T_SOCIABLE": [f"{A} checks on everyone in turn, asking how they're holding up, and actually listens to the answers."],
    "PF_Q_MOTHER_HEN": [f"{A} goes round checking everyone's socks for holes.  Nobody is spared."],
    "PF_Q_HATES_WASTE": [f"{A} scrapes the last bits out of every empty can and stacks the cans in a neat tower."],
    "PF_Q_GALLOWS": [f"{A} adds another tally mark to a board by the door.  Nobody asks what they're counting."],
    "PF_Q_PROUD": [f"{A} practices with their weapon where everyone can see, and pretends not to notice anyone watching."],
    "PF_Q_ROMANTIC": [f"{A} writes something in a notebook and snaps it shut whenever anyone comes near."],
    "PF_Q_GRUDGE": [f"{A} sharpens a knife a little longer than a knife needs sharpening."],
    "PF_Q_LOYAL": [f"{A} walks the edge of the place twice, then a third time, just to be sure."],
    "PF_Q_FORGIVING": [f"{A} brings a cup of something hot to the person they argued with last, and leaves it without a word."],
}
quirk_eff = []
for i, (trait, texts) in enumerate(QUIRK.items()):
    DAY_LINES[f"day_q_{i}"] = texts[0]
    quirk_eff.append({"if": {"and": [{"u_has_trait": trait}, m("pf_day_set == 0"), m("rand(1) == 0"),
                                     m("value_or(u_pf_qday, -1) != floor(time('now') / time('1 d'))")]},
                      "then": [{"set_string_var": f"day_q_{i}", "target_var": g("pf_day_line")}, m("pf_day_set = 1"),
                               m("u_pf_qday = floor(time('now') / time('1 d'))")]})
PAIR = [
    f"{A} shows {B} a card trick.  {B} pretends not to know how it works.",
    f"{A} and {B} argue, at length and with diagrams in the dirt, about whether the dead can swim.",
    f"{A} and {B} split a can of peaches, passing the fork back and forth.",
    f"{A} cuts {B}'s hair with a pair of kitchen scissors.  It could be worse.  It could also be better.",
    f"{A} and {B} talk quietly about before.  Neither of them says what they lost.",
    f"{A} and {B} try to fix a radio together, and get a few seconds of static that has everyone gathering round.",
    f"{A} teaches {B} a song from where they grew up.  {B} gets the words wrong on purpose.",
    # full run day 161: seven lines, and the song came round twice in four hours
    f"{A} and {B} play cards for buttons.  {B} cheats, badly, and {A} lets it go.",
    f"{A} holds the ladder while {B} fixes something on the roof, and offers advice nobody asked for.",
    f"{A} and {B} carry water together, swapping the heavy end without a word.",
    f"{A} and {B} try to remember every flavor of ice cream there ever was.  The list gets long.",
    f"{A} patches {B}'s jacket.  {B} complains about the color of the thread the whole time.",
    f"{A} and {B} plan, in great detail, the garden they will have one day.",
    f"{A} reads aloud to {B} from a water-stained magazine, doing all the voices.",
    f"{A} and {B} take turns at the grindstone, and talk about nothing at all.",
    f"{A} shows {B} how they used to tie a tie.  Neither of them has a tie.",
]
pair_eff, kv = pool("pf_day_pair_last", "day_pair_", PAIR); DAY_LINES.update(kv)
MOURN = [
    f"{A} keeps picking up something that belonged to the one they lost, and putting it down again.",
    f"{A} sits by themselves for a long while.  Someone leaves food next to them, and later it's gone.",  # full run: "afternoon" at 09:00
    f"{A} starts to say something to nobody, stops, and goes back to work.",
    f"{A} works twice as hard as anyone today, and won't stop when they're told to.",
    f"{A} laughs at something, then looks guilty for laughing.",
]
mourn_eff, kv = pool("pf_day_mourn_last", "day_mourn_", MOURN); DAY_LINES.update(kv)
DAY_LINES["day_avoid"] = f"{A} and {B} spend the day carefully not being in the same place."
# full run days 105-109: "Henriette Nguyen sits with you, shoulder to shoulder…", "Mitzi Nunes and Easter Godfrey sit a
# little apart from the others, talking quietly." and "Easter Godfrey brings up something from a while back, and smiles a
# little." word for word, every evening for five nights.  Small pools, spoken through PF_SAY_day.
court_you_eff, kv = pool("pf_court_you_last", "court_you_", [
    f"{A} sits with you, shoulder to shoulder, and for a while neither of you says anything.",
    f"{A} saves you the spot by the fire, and pretends they didn't.",
    f"{A} leans against you while the others talk, warm and heavy and half asleep.",
    f"{A} steals the last bite off your plate, and grins when you notice.",
    f"{A} finds your hand in the dark and holds onto it until the fire burns down.",
    f"{A} tells you something about themselves they haven't told anyone here, very quietly.",
]); DAY_LINES.update(kv)
court_npc_eff, kv = pool("pf_court_npc_last", "court_npc_", [
    f"{A} and {B} sit a little apart from the others, talking quietly.",
    f"{A} and {B} share one blanket and argue about who's hogging it.",
    f"{A} falls asleep against {B}'s shoulder, and {B} doesn't move for an hour.",
    f"{A} and {B} laugh at something nobody else heard.",
    f"{A} braids {B}'s hair by the fire, badly, and neither of them minds.",
    f"{A} and {B} sit with their knees touching, watching the fire, not talking.",
]); DAY_LINES.update(kv)
retell_eff, kv = pool("pf_retell_last", "retell_", [
    f"{A} brings up something from a while back, and smiles a little.",
    f"{A} starts a story with \"Remember when…\", and half the fire groans, because they do.",
    f"{A} laughs out of nowhere at something that happened weeks ago, and has to explain it.",
    f"{A} brings up an old day on the road, and for once it sounds almost funny.",
]); DAY_LINES.update(kv)
files["day.json"] = [
    eoc("PF_DAY_tick", [
        THREAT_SCAN,
        {"if": m("pf_threat == 0"), "then": [
            m("pf_day_n = 0"),
            {"u_run_npc_eocs": ["PF_DAY_one"], "local": True, "npc_range": 25}]},
    ], "Every 90 minutes, 09:00-18:00, when it's calm: up to two people near you do something small on their own or with someone (variety pass, playtest 2).",
        recurrence="90 minutes", **{"global": True},
        condition={"and": [m("time_since('midnight', 'unit': 'hours') >= 9"), m("time_since('midnight', 'unit': 'hours') < 18")]}),
    eoc("PF_DAY_one", [
        {"run_eocs": "PF_ID_ensure"},
        m("pf_day_n += 1"), name_into("pf_say_a"),
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_day_uid")},
        {"set_string_var": "", "target_var": g("pf_day_line")}, m("pf_day_set = 0"),
        m("pf_day_pf = 0"),
        m("pf_day_mourning = time('now') < value_or(u_pf_mourn_until, 0)"),
        {"if": m("(rand(1) == 0) * (pf_day_mourning == 0)"), "then": [{"u_run_npc_eocs": ["PF_DAY_partner"], "local": True, "npc_range": 10}]},
        {"if": m("pf_day_pf == 1"), "then": [
            {"if": m("pf_day_px >= 30"),
             # playtest 3: "...carefully not being in the same place" twice in two hours; once a day, then life goes on
             "then": [{"if": m("value_or(pf_avoid_day, -1) != floor(time('now') / time('1 d'))"),
                       "then": [m("pf_avoid_day = floor(time('now') / time('1 d'))"),
                                {"set_string_var": "day_avoid", "target_var": g("pf_day_line")}, {"run_eocs": "PF_MK_bicker", "beta_talker": g("pf_day_pwho")}],
                       "else": solo_eff}],
             "else": pair_eff + [m("pf_m_str_in = 20"), {"run_eocs": "PF_MK_fire_evening", "beta_talker": g("pf_day_pwho")}]}],
         "else": [{"if": m("pf_day_mourning"), "then": mourn_eff + [m("pf_day_set = 1")]}] + quirk_eff + [
            {"if": m("pf_day_set == 0"), "then": [
                {"if": m("weather('precipitation') > 0"), "then": wet_eff,
                 "else": [{"if": {"and": [{"is_weather": "sunny"}, m("rand(2) == 0")]}, "then": sun_eff, "else": solo_eff}]}]}]},
        {"if": m(DAY_CALM), "then": [{"run_eocs": "PF_SAY_day", "alpha_talker": "avatar"}]},
        m("pf_day_total = value_or(pf_day_total, 0) + 1"),
    ], "u = an adult near you.  Half the time they look for someone within 10 tiles to do something with (tension 30+ in that person's view of them: they avoid each other instead).  Otherwise their quirk (1 in 2, once a day each), the weather, or a general pool.",
        condition={"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18"), m("has_var(u_pf_uid)"), {"not": {"u_has_effect": "sleep"}},
                           m("pf_day_n < 2"), {"or": [m("rand(1) == 0"), m("value_or(pf_day_force, 0) == 1")]}]}),
    eoc("PF_DAY_partner", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": g("pf_day_uid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        {"if": {"or": [m("pf_read_w >= 15"), m("pf_read_x >= 30")]}, "then": [
            m("pf_day_pf = 1"), m("pf_day_px = pf_read_x"), {"u_set_talker": g("pf_day_pwho")}, name_into("pf_say_b")]},
    ], "u = someone within 10 tiles.  Their view of the one acting decides: warm enough (15+) to do something together, or tense enough (30+) to avoid them.",
        condition={"and": [m("pf_day_pf == 0"), {"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18"), m("has_var(u_pf_uid)"),
                           {"not": {"u_has_effect": "sleep"}}, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_day_uid")]}}]}),
    eoc("PF_DAY_rested", [
        m("pf_rest_day = floor(time('now') / time('1 d'))"),
        {"u_run_npc_eocs": [{"id": "PF_DAY_rested_one", "condition": m("has_var(u_pf_uid)"), "effect": [m("u_val('sleepiness') = 0"), m("u_val('sleep_deprivation') = 0")]}], "local": True, "npc_range": 60},
    ], "Once a day around 06:00: our people wake rested.  Without it they never slept for real (non-followers aren't allowed to, and the home bed only adds an effect), so their sleep deprivation climbed past vanilla's threshold and 'lets out a huge yawn' / 'tiredly rubs their eyes' flooded the log all day (suffer.cpp without_sleep; variety pass).",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m("time_since('midnight', 'unit': 'hours') >= 6"), m("time_since('midnight', 'unit': 'hours') < 8"),
                           m("value_or(pf_rest_day, -1) != floor(time('now') / time('1 d'))")]}),
    eoc("PF_NIGHT_bedroll", [
        THREAT_SCAN,
        {"if": m("pf_threat == 0"), "then": [m("pf_bedroll_night = floor((time('now') - time('12 h')) / time('1 d'))"), m("pf_bedroll_n = 0"), {"u_run_npc_eocs": [{"id": "PF_NIGHT_bedroll_one", "effect": [{"u_add_effect": "sleep", "duration": "5 hours"}, m("pf_bedroll_n += 1")],
            "condition": {"and": [m("has_var(u_pf_uid)"), m("value_or(u_pf_resident, 0) == 0"), {"not": {"u_has_effect": "sleep"}},
                                  {"not": {"and": [m("value_or(pf_watch_active, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_watch_uid")]}]}}]}}],
            "local": True, "npc_range": 60}]},
    ], "Once a night, 23:00-01:00, at the first calm check (it retries every 30 minutes while something hostile is around): our people without a bed at home (bands, visitors, children, babies) lie down where they are and sleep about five hours (the vanilla 'sleep' effect: the tileset draws them asleep, and the Horn wakes them).  The night watcher stays up.  Residents use their beds (household.json).",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [{"or": [m("time_since('midnight', 'unit': 'hours') >= 23"), m("time_since('midnight', 'unit': 'hours') < 1")]},
                           m("value_or(pf_bedroll_night, -1) != floor((time('now') - time('12 h')) / time('1 d'))")]}),
    eoc("PF_LINE_court_you", court_you_eff + [{"run_eocs": "PF_SAY_day"}], "u = avatar.  Your sweetheart's moment with you at the fire."),
    eoc("PF_LINE_court_npc", court_npc_eff + [{"run_eocs": "PF_SAY_day"}], "u = avatar.  A couple's moment at the fire (pf_say_a, pf_say_b)."),
    eoc("PF_LINE_retell", retell_eff + [{"run_eocs": "PF_SAY_day"}], "u = avatar.  Someone brings up an old memory (pf_say_a)."),
    eoc("PF_SAY_day", [{"if": {"compare_string": [g("pf_day_line"), k]}, "then": [say(t)]} for k, t in DAY_LINES.items()],
        "u = avatar.  Daytime lines, picked by the global pf_day_line."),
]

for fname, data in files.items():
    json.dump(data, open(os.path.join(OUT, fname), "w", encoding="utf-8", newline="\n"), indent=2)
print("life written:", {k: len(v) for k, v in files.items()})
