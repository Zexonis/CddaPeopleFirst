"""Generates mods/PeopleFirst/family/*.json: v0.3 "Family" (concept §4.4), first pass.

Family links: a child has u_pf_mom / u_pf_dad (uids, or "none") and maybe u_pf_guardian (who took them in); the directory also
publishes them (pf_reg_<child>_p1 / _p2 / _gd) so grief can tell, off-screen, whose child someone was.
Born and adopted children are A-Life persons (unique ids PF_P_n), so the growth tick reaches them anywhere.
HARD RULE (§4.4): children never enter romance, intimacy or pregnancy (PF_CHILD and age, checked again here).

Hooks called from elsewhere: PF_FAM_try_conceive (hearts, a couple's evening), PF_FAM_on_parent_death (hearts grief),
PF_FAM_watch_bonus (life watch), PF_FAM_child_line (life fire activity).

Usage:  python tools/gen_family.py mods/PeopleFirst/family
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
def name_into(gvar, tag="<u_name>"): return {"set_string_var": tag, "target_var": g(gvar), "parse_tags": True}
def regname(uid_global, target):
    return [{"set_string_var": "pf_name_<global_val:%s>" % uid_global, "target_var": ctx("nref"), "parse_tags": True},
            {"copy_var": {"var_val": "nref"}, "target_var": g(target)}]
def regset(uid_global, field, value_math):
    return [{"set_string_var": "pf_reg_<global_val:%s>_%s" % (uid_global, field), "target_var": ctx("rs_" + field), "parse_tags": True},
            m(f"v_rs_{field} = {value_math}")]
def regcopy(uid_global, field, src):
    return [{"set_string_var": "pf_reg_<global_val:%s>_%s" % (uid_global, field), "target_var": ctx("rc_" + field), "parse_tags": True},
            {"copy_var": src, "target_var": {"var_val": "rc_" + field}}]
def cooldown_ok_c(var, dur):
    return {"or": [m(f"time_since({var}) < 0"), m(f"time_since({var}) > time('{dur}')")]}
def line(key): return {"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": key}}
CALM_LINES = "value_or(pf_set_chatter, 1) == 1"
ADULT = {"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18")]}
# growth pace: realistic, accelerated (default: a year of a child's life per game month), fast (testing: a year per 3 game days)
PACE = "(value_or(pf_set_grow, 1) == 0 ? 1 : (value_or(pf_set_grow, 1) == 1 ? 12 : 120))"
TERM_DAYS = "(value_or(pf_set_grow, 1) == 0 ? 270 : (value_or(pf_set_grow, 1) == 1 ? 30 : 3))"

files = {}

# ============================================================ EFFECTS, TRAITS, NPC TEMPLATES
files["defs.json"] = [
    {"type": "effect_type", "id": "PF_preg_1", "name": ["Pregnant (early)"], "desc": ["You're pregnant.  You get hungry more often, and some mornings are rough."],
     "rating": "neutral", "show_in_info": True, "enchantments": [{"condition": "ALWAYS", "values": [{"value": "HUNGER", "multiply": 0.15}]}]},
    {"type": "effect_type", "id": "PF_preg_2", "name": ["Pregnant"], "desc": ["You're pregnant.  You tire sooner and can't carry as much."],
     "rating": "neutral", "show_in_info": True, "enchantments": [{"condition": "ALWAYS", "values": [
         {"value": "HUNGER", "multiply": 0.25}, {"value": "CARRY_WEIGHT", "add": -5000}, {"value": "MAX_STAMINA", "multiply": -0.1}]}]},
    {"type": "effect_type", "id": "PF_preg_3", "name": ["Pregnant (late)"], "desc": ["You're heavily pregnant.  You're slower, tire quickly, need more sleep, and can't carry much."],
     "rating": "neutral", "show_in_info": True, "enchantments": [{"condition": "ALWAYS", "values": [
         {"value": "HUNGER", "multiply": 0.3}, {"value": "CARRY_WEIGHT", "add": -10000}, {"value": "MAX_STAMINA", "multiply": -0.25},
         {"value": "SPEED", "multiply": -0.15}, {"value": "SLEEPINESS", "multiply": 0.3}]}]},
    {"type": "effect_type", "id": "PF_infant", "name": ["Infant"], "desc": ["A baby.  Can barely move on their own."],
     "//": "MUTE: babies don't bark vanilla combat lines ('Fuck this, go!' from an infant, 2026-10-11 test).",
     "rating": "neutral", "show_in_info": True, "flags": ["MUTE"], "enchantments": [{"condition": "ALWAYS", "values": [{"value": "SPEED", "multiply": -0.9}]}]},
    {"type": "effect_type", "id": "PF_carrying_baby", "name": ["Carrying a baby"], "desc": ["You have a baby in your arms or on your back."],
     "rating": "neutral", "show_in_info": True, "enchantments": [{"condition": "ALWAYS", "values": [{"value": "CARRY_WEIGHT", "add": -4000}]}]},
    {"type": "effect_type", "id": "PF_partner_carries", "name": ["Partner carrying the load"], "desc": ["Your partner is carrying the heavy stuff for you."],
     "rating": "good", "show_in_info": True, "enchantments": [{"condition": "ALWAYS", "values": [{"value": "CARRY_WEIGHT", "add": 7000}]}]},
    {"type": "effect_type", "id": "PF_toddler", "name": ["Toddler"], "desc": ["Little legs.  They get tired fast and need a hand."],
     "rating": "neutral", "show_in_info": True, "enchantments": [{"condition": "ALWAYS", "values": [{"value": "SPEED", "multiply": -0.35}]}]},
    {"type": "morale_type", "id": "PF_morale_newparent", "text": "New parent"},
    {"type": "morale_type", "id": "PF_morale_childloss", "text": "Lost a child"},
    {"type": "npc", "id": "PF_FAM_BABY", "//": "A newborn: tiny, a child, nearly immobile (PF_infant).  Stays where it was laid down (mission 2).",
     "name_suffix": "baby", "class": "NC_NONE", "attitude": 0, "mission": 2, "faction": "no_faction", "chat": "TALK_PF_BABY"},
    {"type": "talk_topic", "id": "TALK_PF_BABY",
     "dynamic_line": "*the baby looks up at you and grabs at your finger*",
     "responses": [{"text": "*let them hold on for a while*", "topic": "TALK_DONE"}]},
    {"type": "talk_topic", "id": "TALK_PF_KID",
     "dynamic_line": {"math": ["value_or(n_pf_needs_home, 0) == 1"],
                      "yes": "*won't look at you*  Everyone keeps saying it'll be okay.  It's not okay.",
                      "no": "Did you know you can tell how far away a storm is by counting?  I can count really high."},
     "responses": [{"text": "Stay close to the grown-ups.", "topic": "TALK_DONE"}]},
]

# ============================================================ PREGNANCY
files["pregnancy.json"] = [
    eoc("PF_FAM_try_conceive", [
        m("pf_fm_u_f = u_gender() == 0"),
        {"if": m("pf_fm_u_f"),
         "then": [{"run_eocs": "PF_FAM_conceive", "beta_talker": "npc"}],
         "else": [{"run_eocs": "PF_FAM_conceive", "alpha_talker": "npc", "beta_talker": "u"}]},
    ], "Alpha and beta = partners spending an evening together (called from the hearts couple check when nothing else happened).  Intimacy is implied, never shown.  A small chance each such evening; only adults, never children, one man and one woman (she 45 or younger), neither already expecting, nobody in mourning, and only if pregnancy is on in Settings.",
        condition={"and": [m("value_or(pf_set_preg, 1) == 1"), m("value_or(u_pf_rel_stage, 0) >= 2"),
                           ADULT, {"not": {"npc_has_trait": "PF_CHILD"}}, m("n_val('age') >= 18"),
                           m("u_gender() != n_gender()"),
                           # full run day 118: Henriette, 55, married Dante and was rolling 8% a night.  Mothers are 45 or younger.
                           m("(u_gender() == 0) * u_val('age') + (n_gender() == 0) * n_val('age') <= 45"),
                           m("value_or(u_pf_preg, 0) == 0"), m("value_or(n_pf_preg, 0) == 0"),
                           m("time('now') >= value_or(u_pf_mourn_until, 0)"), m("time('now') >= value_or(n_pf_mourn_until, 0)"),
                           m("rand(99) < value_or(pf_set_preg_chance, 8)")]}),
    eoc("PF_FAM_conceive", [
        m("u_pf_preg = 1"), m("u_pf_preg_t = time('now')"), m("u_pf_preg_stage = 0"), m("u_pf_preg_known = 0"),
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": {"u_val": "pf_preg_father"}},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_fm_new")},
        {"run_eocs": "PF_FAM_track_mother"},
        m("pf_conceptions_total = value_or(pf_conceptions_total, 0) + 1"),
    ], "Alpha = the mother, beta = the father.  Nobody knows yet: morning sickness gives it away later."),
    eoc("PF_FAM_band_conceive", [
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_fm_dad")},
        {"set_string_var": "pf_reg_<global_val:pf_fm_dad>_g", "target_var": ctx("dg"), "parse_tags": True},
        {"if": m("value_or(v_dg, 0) == 1"), "then": [
            m("u_pf_preg = 1"), m("u_pf_preg_t = time('now')"), m("u_pf_preg_stage = 0"), m("u_pf_preg_known = 0"),
            {"copy_var": g("pf_fm_dad"), "target_var": {"u_val": "pf_preg_father"}},
            {"run_eocs": "PF_FAM_track_mother"},
            m("pf_conceptions_total = value_or(pf_conceptions_total, 0) + 1"),
            m("pf_band_conceptions_total = value_or(pf_band_conceptions_total, 0) + 1")]},
    ], "u = a woman in an off-screen band at camp (by unique id), whose partner camps with her.  The same small chance as at the fire.  Off-screen she moves through her pregnancy by unique id; the birth waits until she's near you.",
        condition={"and": [m("value_or(pf_set_preg, 1) == 1"), m("u_gender() == 0"), ADULT, m("u_val('age') <= 45"), m("value_or(u_pf_has_sweet, 0) == 1"),
                           m("value_or(u_pf_rel_stage, 0) >= 2"), m("value_or(u_pf_preg, 0) == 0"), m("time('now') >= value_or(u_pf_mourn_until, 0)"),
                           {"not": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}},
                           m("rand(99) < value_or(pf_set_preg_chance, 8)")]}),
    eoc("PF_FAM_track_mother", [
        m("pf_fm_i = value_or(pf_moms_n, 0) % 12"),
        {"set_string_var": "pf_mom_<global_val:pf_fm_i>", "target_var": ctx("mr"), "parse_tags": True},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "mr"}},
        m("pf_moms_n = value_or(pf_moms_n, 0) + 1"),
    ], "u = an expecting mother.  Remembered in a small ring so the daily tick can find her (in the bubble by uid, or by unique id)."),
    eoc("PF_FAM_preg_tick", [
        m("pf_fm_k = 0"), m("pf_fm_waiting = 0"),
        {"run_eocs": "PF_FAM_preg_tick_k", "condition": m("pf_fm_k < min(value_or(pf_moms_n, 0), 12)"), "iterations": 13},
    ], "Every 6 hours: every expecting mother moves along (stage, discovery, birth when due).",
        recurrence="6 hours", **{"global": True}),
    eoc("PF_FAM_preg_tick_k", [
        {"set_string_var": "pf_mom_<global_val:pf_fm_k>", "target_var": ctx("mr"), "parse_tags": True},
        {"copy_var": {"var_val": "mr"}, "target_var": g("pf_find_uid")},
        {"set_string_var": "pf_reg_<global_val:pf_find_uid>_dead", "target_var": ctx("md"), "parse_tags": True},
        {"if": m("value_or(v_md, 0) == 1"), "then": [{"set_string_var": "none", "target_var": {"var_val": "mr"}}, {"set_string_var": "none", "target_var": g("pf_find_uid")}]},
        m("pf_fm_onscreen = 1"),
        {"if": {"compare_string": [g("pf_find_uid"), "none"]}, "then": [m("pf_fm_onscreen = -1")]},
        {"if": {"compare_string": [g("pf_find_uid"), "AVATAR"]},
         "then": [{"run_eocs": "PF_FAM_preg_step", "alpha_talker": "avatar"}],
         "else": [{"run_eocs": "PF_FIND_by_uid", "alpha_talker": "avatar"},
                  {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_FAM_preg_step", "alpha_talker": g("pf_find_who")}],
                   "else": [{"run_eocs": {"id": "PF_FAM_preg_offscreen", "condition": m("pf_fm_onscreen == 1"), "effect": [m("pf_fm_onscreen = 0"),
                            {"u_run_npc_eocs": ["PF_FAM_preg_step"], "unique_ids": [g("pf_find_uid")], "local": False}]}}]}]},
        m("pf_fm_k += 1"),
    ]),
    eoc("PF_FAM_preg_step", [
        m("pf_fm_p = (time('now') - u_pf_preg_t) / time('1 d') / %s" % TERM_DAYS),
        m("pf_fm_st = 1 + (pf_fm_p >= 0.33) + (pf_fm_p >= 0.66)"),
        {"if": m("pf_fm_st != value_or(u_pf_preg_stage, 0)"), "then": [
            {"u_lose_effect": ["PF_preg_1", "PF_preg_2", "PF_preg_3"]},
            {"if": m("pf_fm_st == 1"), "then": [{"u_add_effect": "PF_preg_1", "duration": "PERMANENT"}]},
            {"if": m("pf_fm_st == 2"), "then": [{"u_add_effect": "PF_preg_2", "duration": "PERMANENT"}]},
            {"if": m("pf_fm_st == 3"), "then": [{"u_add_effect": "PF_preg_3", "duration": "PERMANENT"}]},
            m("u_pf_preg_stage = pf_fm_st")]},
        {"if": {"and": [m("pf_fm_p < 0.33"), m("rand(2) == 0")]}, "then": [{"u_add_effect": "nausea", "duration": "20 minutes"}]},
        {"if": {"and": [m("value_or(u_pf_preg_known, 0) == 0"), m("pf_fm_p >= 0.12"), m("pf_fm_onscreen == 0")]}, "then": [m("u_pf_preg_known = 1")]},
        {"if": {"and": [m("value_or(u_pf_preg_known, 0) == 0"), m("pf_fm_p >= 0.12")]}, "then": [
            m("u_pf_preg_known = 1"), name_into("pf_say_a"),
            {"copy_var": {"u_val": "pf_preg_father"}, "target_var": g("pf_fm_dad")}] + regname("pf_fm_dad", "pf_say_b") + [
            {"if": {"compare_string": [g("pf_fm_dad"), "AVATAR"]}, "then": [{"set_string_var": "you", "target_var": g("pf_say_b")}]},
            {"if": "u_is_avatar", "then": [line("preg_you")], "else": [line("preg_npc")]}]},
        {"if": {"and": [m("pf_fm_p >= 1"), m("pf_fm_onscreen == 1")]}, "then": [{"run_eocs": "PF_FAM_birth"}]},
        {"if": {"and": [m("pf_fm_p >= 1"), m("pf_fm_onscreen == 0")]}, "then": [m("pf_fm_waiting += 1")]},
        {"if": {"and": ["u_is_avatar", m("pf_fm_st >= 2"), m("rand(2) == 0")]}, "then": [{"run_eocs": "PF_FAM_craving"}]},
    ], "u = an expecting mother (found on-screen this turn, or reached off-screen by unique id with pf_fm_onscreen = 0: then nobody sees the news, and the birth waits until she's near you).  Stage effects (hunger, then carry weight and stamina, then speed and sleep), morning sickness early on, the news at about an eighth of the way, birth at term.",
        condition=m("value_or(u_pf_preg, 0) == 1")),
]
# fix: the bonus has to come back through a global
files["pregnancy.json"] += [
    eoc("PF_FAM_craving", [
        m("pf_crave_last = time('now')"),
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_find_uid")},
        {"run_eocs": "PF_FIND_by_uid"},
        {"u_location_variable": g("pf_fm_avpos")},
        {"if": m("pf_find_ok == 1"),
         "then": [{"run_eocs": "PF_FAM_bring_sweet", "alpha_talker": g("pf_find_who"), "beta_talker": "avatar"}],
         "else": [line("crave_alone")]},
    ], "u = you, pregnant (stage 2+).  A craving; if the one you're with is around, they find you something sweet (once a day at most).",
        condition={"and": [m("value_or(u_pf_has_sweet, 0) == 1"), cooldown_ok_c("pf_crave_last", "1 d")]}),
    eoc("PF_FAM_bring_sweet", [
        name_into("pf_say_a"),
        m("_r = rand(2)"),
        {"if": m("_r == 0"), "then": [{"run_eocs": "PF_GIVE_chocolate", "alpha_talker": "avatar"}, {"set_string_var": "a bar of chocolate", "target_var": g("pf_say_b")}]},
        {"if": m("_r == 1"), "then": [{"run_eocs": "PF_GIVE_candy", "alpha_talker": "avatar"}, {"set_string_var": "a handful of hard candy", "target_var": g("pf_say_b")}]},
        {"if": m("_r == 2"), "then": [{"run_eocs": "PF_GIVE_cookies", "alpha_talker": "avatar"}, {"set_string_var": "a battered pack of cookies", "target_var": g("pf_say_b")}]},
        line("crave_brought"),
        m("pf_m_str_in = 50"), {"run_eocs": "PF_MK_care_given"},
    ], "Alpha = your partner, beta = you."),
]
files["pregnancy.json"].append(eoc("PF_FAM_watch_bonus", [
    m("pf_fm_watch_add = 0"),
    {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}]}, "then": [
        {"run_eocs": {"id": "PF_FAM_watch_av", "effect": [m("pf_fm_avpreg = value_or(u_pf_preg, 0)")]}, "alpha_talker": "avatar"},
        {"if": m("pf_fm_avpreg == 1"), "then": [m("pf_fm_watch_add = 25")]}]},
], "u = a would-be watcher.  The partner of an expecting mother (you) takes her watch: +25, returned in pf_fm_watch_add."))

# ============================================================ BIRTH
files["birth.json"] = [
    eoc("PF_FAM_birth", [
        m("u_pf_preg = 0"), {"u_lose_effect": ["PF_preg_1", "PF_preg_2", "PF_preg_3"]},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_fm_mom")},
        {"copy_var": {"u_val": "pf_preg_father"}, "target_var": g("pf_fm_dad")},
        # full run day 169: Janey Hammond had the first watch the night she gave birth (gen_town PF_TWATCH_cand reads these)
        m("u_pf_birth_t = time('now')"), {"copy_var": g("pf_fm_dad"), "target_var": g("pf_last_birth_dad")}, m("pf_last_birth_t = time('now')"),
        name_into("pf_say_a"),
        {"run_eocs": "PF_ALIFE_register_person"},
        {"set_string_var": "the baby", "target_var": g("pf_fm_babyname")},
        {"u_spawn_npc": "PF_FAM_BABY", "unique_id": g("pf_person_uid"), "real_count": 1, "traits": ["PF_CHILD", "SMALL2"], "min_radius": 1, "max_radius": 2},
        {"u_run_npc_eocs": ["PF_FAM_newborn"], "unique_ids": [g("pf_person_uid")], "local": False},
        # full run day 151: Golly Whitmore gave birth at her band's camp, the band set off at 06:00, and Marylin was left
        # alone in the grass: a baby only followed its carrier within 60 tiles of you, and off-screen not at all.  A baby
        # born in a band joins the band (it travels with it off-screen and is placed with it when it comes back).
        {"copy_var": g("pf_person_uid"), "target_var": g("pf_fm_lnk_baby")}, m("pf_fm_lnk_ok = 0"),
        {"run_eocs": "PF_FAM_band_baby_leader"},
        {"if": m("pf_fm_lnk_ok == 1"), "then": [{"run_eocs": "PF_BAND_link"}]},
        m("u_pf_kids_n = value_or(u_pf_kids_n, 0) + 1"),
        {"if": "u_is_avatar",
         "then": [{"if": m("(time_since('midnight', 'unit': 'hours') >= 5) * (time_since('midnight', 'unit': 'hours') < 12)"), "then": [line("birth_you")], "else": [line("birth_you_day")]}, {"u_add_morale": "PF_morale_newparent", "bonus": 30, "max_bonus": 40, "duration": "5 d", "decay_start": "2 d"}],
         "else": [{"if": m("value_or(pf_aw_birthing, 0) == 1"), "then": [line("birth_npc_away")], "else": [
             # full run: "By morning…" was said at 23:00.  The night version only in the morning.
             {"if": m("(time_since('midnight', 'unit': 'hours') >= 5) * (time_since('midnight', 'unit': 'hours') < 12)"), "then": [line("birth_npc")], "else": [line("birth_npc_day")]}]}]},
        m("pf_births_total = value_or(pf_births_total, 0) + 1"),
        {"set_string_var": "birth", "target_var": g("pf_ev_new_kind")},
        {"copy_var": g("pf_fm_babyname"), "target_var": g("pf_ev_new_name")},
        m("pf_ev_new_you = 0"), {"if": "u_is_avatar", "then": [m("pf_ev_new_you = 1")]},
        {"copy_var": g("pf_fm_babyname"), "target_var": g("pf_ev_new_youname")},
        {"run_eocs": "PF_HEART_event_add"},
    ], "u = the mother, at term.  A community event: the baby (a real, nearly immobile NPC with a unique id) is born near her, everyone around shares it, and it becomes a birthday to remember."),
    eoc("PF_FAM_band_baby_leader", [
        {"if": m("value_or(u_pf_is_leader, 0) == 1"), "then": [{"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_link_leader")}],
         "else": [{"copy_var": {"u_val": "pf_leader"}, "target_var": g("pf_link_leader")}]},
        {"copy_var": g("pf_fm_lnk_baby"), "target_var": g("pf_link_member")},
        m("pf_fm_lnk_ok = 1"),
    ], "u = a baby's mother (or carrier).  If she travels with an A-Life band, names the band's leader and the baby for PF_BAND_link (run by the caller: one off-screen talker at a time) and sets pf_fm_lnk_ok.",
        condition={"and": [m("value_or(u_pf_band, 0) > 0"), m("value_or(u_pf_resident, 0) == 0"),
                           {"or": [m("value_or(u_pf_is_leader, 0) == 1"), m("has_var(u_pf_leader)")]}]}),
    eoc("PF_FAM_newborn", [
        {"run_eocs": "PF_ALIFE_store_uid"},
        {"run_eocs": "PF_ID_ensure"},
        m("u_val('age') = 0"), m("u_pf_adult = 0"), m("u_pf_rom = 0"), m("u_pf_rom_rolled = 1"),
        {"u_add_effect": "PF_infant", "duration": "PERMANENT"},
        {"copy_var": g("pf_fm_mom"), "target_var": {"u_val": "pf_mom"}},
        {"copy_var": g("pf_fm_dad"), "target_var": {"u_val": "pf_dad"}},
        {"set_string_var": "none", "target_var": {"u_val": "pf_guardian"}},
        m("u_pf_born_t = time('now')"), m("u_pf_kid_stage = 0"), m("u_pf_follow = 2"),
        {"copy_var": g("pf_fm_mom"), "target_var": {"u_val": "pf_carrier"}},
        {"run_eocs": "PF_REG_write"},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_fm_baby")},
    ] + regcopy("pf_fm_baby", "p1", g("pf_fm_mom")) + regcopy("pf_fm_baby", "p2", g("pf_fm_dad")) + [
        {"run_eocs": "PF_ENGINE_name_baby"},
        name_into("pf_fm_babyname"),
        m("pf_fm_ki = value_or(pf_kids_n, 0) % 30"),
        {"set_string_var": "pf_kid_<global_val:pf_fm_ki>", "target_var": ctx("kr"), "parse_tags": True},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "kr"}},
        m("pf_kids_n = value_or(pf_kids_n, 0) + 1"),
        {"u_run_npc_eocs": ["PF_FAM_witness_birth"], "local": True, "npc_range": 20},
        {"run_eocs": "PF_FAM_witness_birth_av", "alpha_talker": "avatar"},
    ], "u = the newborn (reached by unique id right after spawning).  Records parents, birth time and stage, and lists the child for the growth tick."),
    eoc("PF_FAM_witness_birth", [
        {"run_eocs": "PF_ID_ensure"},
        {"if": {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_fm_baby")]}}, "then": [
            {"copy_var": g("pf_fm_mom"), "target_var": g("pf_m_other")},
            m("pf_mv_role = 3"), m("pf_m_str_in = 80"), {"run_eocs": "PF_MV_birth"}]},
    ], "u = someone near a birth.  They were there: a strong memory, and warmth toward the mother."),
    eoc("PF_FAM_witness_birth_av", [
        {"copy_var": g("pf_fm_baby"), "target_var": g("pf_m_other")},
        m("pf_mv_role = 1"), m("pf_m_str_in = 90"), {"run_eocs": "PF_MV_birth"},
    ], "u = you.  A birth in your camp goes in your journal.",
        condition={"or": [{"compare_string": [g("pf_fm_mom"), "AVATAR"]}, {"compare_string": [g("pf_fm_dad"), "AVATAR"]}, m("pf_fm_near_av == 1")]}),
]
# the avatar's journal entry for a birth needs to know whether you were there
files["birth.json"][0]["effect"].insert(0, {"u_location_variable": g("pf_fm_mompos")})
files["birth.json"][0]["effect"].insert(1, {"run_eocs": {"id": "PF_FAM_near_av", "effect": [
    {"u_location_variable": g("pf_fm_avpos")}, m("pf_fm_near_av = distance(pf_fm_avpos, pf_fm_mompos) <= 20")]}, "alpha_talker": "avatar"})

# ============================================================ BABIES (care) and CHILDREN (follow, grow up)
KIDS = 30
grow_k = []
files["children.json"] = [
    eoc("PF_FAM_baby_tick", [
        {"u_run_npc_eocs": ["PF_FAM_baby_one"], "local": True, "npc_range": 60},
    ], "Every 4 hours: each baby in the bubble gets looked after by whoever cares most nearby (parents first).",
        recurrence="4 hours", **{"global": True}, condition=m("value_or(pf_kids_n, 0) > 0")),
    eoc("PF_FAM_baby_one", [
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_fm_baby")},
        {"copy_var": {"u_val": "pf_mom"}, "target_var": g("pf_fm_mom")}, {"copy_var": {"u_val": "pf_dad"}, "target_var": g("pf_fm_dad")},
        name_into("pf_say_b"),
        {"u_location_variable": g("pf_fm_babypos")},
        m("pf_fm_best = -1"),
        {"u_run_npc_eocs": ["PF_FAM_carer_cand"], "local": True, "npc_range": 30},
        {"if": m("pf_fm_best >= 0"), "then": [{"run_eocs": "PF_FAM_tend_baby", "alpha_talker": g("pf_fm_carer"), "beta_talker": "u"}]},
    ], "u = a baby.",
        condition={"and": [m("value_or(u_pf_kid_stage, -1) == 0"), {"u_has_effect": "PF_infant"}]}),
    eoc("PF_FAM_carer_cand", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": g("pf_fm_baby"), "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("_score = pf_read_w + 5"),
        {"if": {"or": [{"compare_string": [{"u_val": "pf_uid"}, g("pf_fm_mom")]}, {"compare_string": [{"u_val": "pf_uid"}, g("pf_fm_dad")]}]}, "then": [m("_score += 50")]},
        {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("_score += 20")]},
        {"if": {"and": [m("_score > pf_fm_best"), m("_score >= 5")]}, "then": [m("pf_fm_best = _score"), {"u_set_talker": g("pf_fm_carer")}]},
    ], "u = an adult near the baby.  Parents first (+50), then mother hens (+20), then anyone fond of the baby.",
        condition=ADULT),
    eoc("PF_FAM_tend_baby", [
        name_into("pf_say_a"),
        {"copy_var": g("pf_fm_babypos"), "target_var": {"u_val": "pf_walk_to"}},
        {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": 1},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
        m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_parenting"},
        {"if": {"and": [m(CALM_LINES), m("rand(2) == 0"), m("value_or(pf_baby_line_t, -1) < time('now') - time('3 h')")]}, "then": [
            m("pf_baby_line_t = time('now')"),
            m("_r = rand(2)"),
            {"if": m("_r == 0"), "then": [line("baby_rock")]},
            {"if": m("_r == 1"), "then": [line("baby_feed")]},
            {"if": m("_r == 2"), "then": [line("baby_sing")]}]},
        {"if": {"or": [{"compare_string": [g("pf_fm_mom"), "AVATAR"]}, {"compare_string": [g("pf_fm_dad"), "AVATAR"]}]}, "then": [
            {"if": {"not": "u_is_avatar"}, "then": [
                {"if": {"and": [m(CALM_LINES), m("value_or(pf_baby_rest_t, -1) < time('now') - time('12 h')")]}, "then": [m("pf_baby_rest_t = time('now')"), line("baby_for_you")]},
                m("pf_m_str_in = 45"), {"run_eocs": "PF_MK_care_given", "beta_talker": "avatar"}]}]},
    ], "Alpha = the carer, beta = the baby.  Walks over, settles them (a parenting moment); if it's your baby, they take it so you can rest (care for you too)."),
    eoc("PF_FAM_grow_tick", [
        m("pf_fm_k = 0"),
        {"run_eocs": "PF_FAM_grow_k", "condition": m("pf_fm_k < min(value_or(pf_kids_n, 0), %d)" % KIDS), "iterations": KIDS + 1},
    ], "Once a day: every child born or taken in grows (by unique id, wherever they are).",
        recurrence="1 day", **{"global": True}, condition=m("value_or(pf_kids_n, 0) > 0")),
    # 2026-10-15: ages and pregnancies are (time since birth or conception) x the pace, so switching Settings → Growing up
    # from accelerated to fast made every child ten times older at once.  The switch rebases them: same age, same progress,
    # new pace from now on.  pf_pace_old / pf_term_old are set by PF_SET_grow before the toggle.
    eoc("PF_FAM_repace", [
        m("pf_fm_k = 0"),
        {"run_eocs": "PF_FAM_repace_k", "condition": m("pf_fm_k < min(value_or(pf_kids_n, 0), %d)" % KIDS), "iterations": KIDS + 1},
        m("pf_fm_k = 0"),
        {"run_eocs": "PF_FAM_repace_m", "condition": m("pf_fm_k < min(value_or(pf_moms_n, 0), 12)"), "iterations": 13},
    ], "u = avatar.  The Growing up pace changed: every child keeps their age and every mother her progress."),
    eoc("PF_FAM_repace_k", [
        {"set_string_var": "pf_kid_<global_val:pf_fm_k>", "target_var": ctx("kr"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "kr"}, "none"]}}, "then": [
            {"u_run_npc_eocs": [{"id": "PF_FAM_repace_kid", "condition": m("has_var(u_pf_born_t)"),
                                 "effect": [m("u_pf_born_t = time('now') - (time('now') - u_pf_born_t) * pf_pace_old / %s" % PACE)]}],
             "unique_ids": [{"var_val": "kr"}], "local": False}]},
        m("pf_fm_k += 1"),
    ]),
    eoc("PF_FAM_repace_m", [
        {"set_string_var": "pf_mom_<global_val:pf_fm_k>", "target_var": ctx("mr"), "parse_tags": True},
        {"if": {"compare_string": [{"var_val": "mr"}, "AVATAR"]},
         "then": [{"run_eocs": "PF_FAM_repace_mom", "alpha_talker": "avatar"}],
         "else": [{"if": {"not": {"compare_string": [{"var_val": "mr"}, "none"]}}, "then": [
             {"u_run_npc_eocs": ["PF_FAM_repace_mom"], "unique_ids": [{"var_val": "mr"}], "local": False}]}]},
        m("pf_fm_k += 1"),
    ]),
    eoc("PF_FAM_repace_mom", [m("u_pf_preg_t = time('now') - (time('now') - u_pf_preg_t) * %s / pf_term_old" % TERM_DAYS)],
        "u = an expecting mother: the same share of the term done, at the new pace.", condition=m("has_var(u_pf_preg_t)")),
    eoc("PF_FAM_grow_k", [
        {"set_string_var": "pf_kid_<global_val:pf_fm_k>", "target_var": ctx("kr"), "parse_tags": True},
        {"copy_var": {"var_val": "kr"}, "target_var": g("pf_fm_kuid")},
        {"set_string_var": "pf_reg_<global_val:pf_fm_kuid>_dead", "target_var": ctx("kd"), "parse_tags": True},
        {"if": m("value_or(v_kd, 0) == 1"), "then": [{"set_string_var": "none", "target_var": {"var_val": "kr"}}]},
        {"if": {"not": {"compare_string": [{"var_val": "kr"}, "none"]}}, "then": [
            {"u_run_npc_eocs": ["PF_FAM_grow"], "unique_ids": [{"var_val": "kr"}], "local": False}]},
        m("pf_fm_k += 1"),
    ]),
    eoc("PF_FAM_grow", [
        m("pf_fm_age = (time('now') - u_pf_born_t) / time('1 d') * %s / 364" % PACE),
        m("pf_fm_stage = (pf_fm_age >= 2) + (pf_fm_age >= 18)"),
        {"if": m("u_val('age') != min(floor(pf_fm_age), 18)"), "then": [m("u_val('age') = min(floor(pf_fm_age), 18)")]},
        {"if": {"and": [m("pf_fm_stage >= 1"), m("u_pf_kid_stage == 0")]}, "then": [
            m("u_pf_kid_stage = 1"), m("u_pf_follow = 1"), {"u_lose_effect": "PF_infant"}, {"set_string_var": "none", "target_var": {"u_val": "pf_carrier"}},
            name_into("pf_say_a"), line("first_steps")]},
        {"if": {"and": [m("u_pf_kid_stage == 1"), m("pf_fm_age < 5"), {"not": {"u_has_effect": "PF_toddler"}}]},
         "then": [{"u_add_effect": "PF_toddler", "duration": "PERMANENT"}]},
        {"if": {"and": [m("pf_fm_age >= 5"), {"u_has_effect": "PF_toddler"}]}, "then": [
            {"u_lose_effect": "PF_toddler"},
            {"if": m("value_or(u_pf_follow, 0) == 2"), "then": [m("u_pf_follow = 1"), {"set_string_var": "none", "target_var": {"u_val": "pf_carrier"}}]},
            name_into("pf_say_a"), line("big_kid")]},
        {"if": {"and": [m("pf_fm_stage >= 2"), m("u_pf_kid_stage == 1")]}, "then": [{"run_eocs": "PF_FAM_grown_up"}]},
    ], "u = a child (by unique id).  Age in years follows the growth pace; babies start walking at 2 and follow their family; from 2 to 5 they're toddlers (slow, carried when they tire, a hand to hold); at 18 they grow up.",
        condition=m("has_var(u_pf_born_t)")),
    eoc("PF_FAM_grown_up", [
        m("u_pf_kid_stage = 2"), m("u_pf_follow = 0"), m("u_pf_needs_home = 0"),
        {"u_lose_trait": "PF_CHILD"}, {"u_lose_trait": "SMALL2"},
        {"copy_var": {"u_val": "pf_mom"}, "target_var": g("pf_fm_mom")}, {"copy_var": {"u_val": "pf_dad"}, "target_var": g("pf_fm_dad")},
        {"set_string_var": "pf_reg_<global_val:pf_fm_mom>_tm", "target_var": ctx("tm1"), "parse_tags": True},
        {"set_string_var": "pf_reg_<global_val:pf_fm_dad>_tm", "target_var": ctx("tm2"), "parse_tags": True},
        {"set_string_var": "pf_reg_<global_val:pf_fm_mom>_q", "target_var": ctx("q1"), "parse_tags": True},
        {"set_string_var": "pf_reg_<global_val:pf_fm_dad>_q", "target_var": ctx("q2"), "parse_tags": True},
        {"u_lose_trait": "PF_T_SOCIABLE"}, {"u_lose_trait": "PF_T_LONER"},
        m("_tm = rand(1) == 0 ? value_or(v_tm1, 0) : value_or(v_tm2, 0)"),
        {"if": m("_tm == 1"), "then": [{"u_add_trait": "PF_T_SOCIABLE"}]},
        {"if": m("_tm == 2"), "then": [{"u_add_trait": "PF_T_LONER"}]},
        m("_q = rand(4) == 0 ? rand(7) : (rand(1) == 0 ? value_or(v_q1, -1) : value_or(v_q2, -1))"),
        {"if": m("_q >= 0"), "then": [
            {"u_lose_trait": "PF_Q_LOYAL"}, {"u_lose_trait": "PF_Q_HATES_WASTE"}, {"u_lose_trait": "PF_Q_MOTHER_HEN"}, {"u_lose_trait": "PF_Q_GALLOWS"},
            {"u_lose_trait": "PF_Q_PROUD"}, {"u_lose_trait": "PF_Q_GRUDGE"}, {"u_lose_trait": "PF_Q_FORGIVING"}, {"u_lose_trait": "PF_Q_ROMANTIC"},
            {"switch": m("_q"), "cases": [
                {"case": 0, "effect": {"u_add_trait": "PF_Q_LOYAL"}}, {"case": 1, "effect": {"u_add_trait": "PF_Q_HATES_WASTE"}},
                {"case": 2, "effect": {"u_add_trait": "PF_Q_MOTHER_HEN"}}, {"case": 3, "effect": {"u_add_trait": "PF_Q_GALLOWS"}},
                {"case": 4, "effect": {"u_add_trait": "PF_Q_PROUD"}}, {"case": 5, "effect": {"u_add_trait": "PF_Q_GRUDGE"}},
                {"case": 6, "effect": {"u_add_trait": "PF_Q_FORGIVING"}}, {"case": 7, "effect": {"u_add_trait": "PF_Q_ROMANTIC"}}]}]},
        m("u_pf_rom_rolled = 0"), {"run_eocs": "PF_ROM_roll"},
        # KinfoldLab: six "isn't a child anymore" lines in a row, the same for your own child and a band child you never met
        name_into("pf_say_a"), m("pf_gu_rot = (value_or(pf_gu_rot, -1) + 1) % 3"), m("_g = pf_gu_rot"),  # in turn: several often grow up the same day
        {"if": {"or": [{"compare_string": [{"u_val": "pf_guardian"}, "AVATAR"]}, {"compare_string": [{"u_val": "pf_mom"}, "AVATAR"]}, {"compare_string": [{"u_val": "pf_dad"}, "AVATAR"]}]}, "then": [{"if": m("_g == 0"), "then": [line("grown_up_yours_0")]}, {"if": m("_g == 1"), "then": [line("grown_up_yours_1")]},
                               {"if": m("_g == 2"), "then": [line("grown_up_yours_2")]}],
         "else": [{"if": m("value_or(u_pf_resident, 0) == 1"), "then": [
             {"if": m("_g == 0"), "then": [line("grown_up")]}, {"if": m("_g == 1"), "then": [line("grown_up_1")]}, {"if": m("_g == 2"), "then": [line("grown_up_2")]}]}]},
        m("pf_grownup_total = value_or(pf_grownup_total, 0) + 1"),
    ], "u = a child turning 18.  No longer a child: the PF_CHILD and tiny-body traits go, they inherit a temperament from one parent and a quirk from one parent (or, one time in five, their own), and only now do they get a romantic nature."),
    eoc("PF_FAM_follow_tick", [
        {"u_run_npc_eocs": ["PF_FAM_follow_one", "PF_FAM_carry_one"], "local": True, "npc_range": 60},
        {"run_eocs": "PF_FAM_partner_helps", "alpha_talker": "avatar"},
    ], "Every 5 minutes: children in the bubble stay near their family (guardian, else mother, else father).  On-screen only; a walk order, like everything else that moves people.",
        recurrence="5 minutes", **{"global": True}, condition=m("value_or(pf_kids_n, 0) + value_or(pf_adoptions_total, 0) > 0")),
    # full run day 151: Dante carried Marylin Whitmore 50 tiles in under a minute; she was still 51 tiles back when he
    # looked (the 5-minute step), and a few more steps would have put her out of the step's 60-tile reach for good.
    eoc("PF_FAM_carry_quick", [
        {"u_run_npc_eocs": [{"id": "PF_FAM_carry_quick_one", "condition": {"compare_string": [{"u_val": "pf_carrier"}, "AVATAR"]},
                             "effect": [{"run_eocs": "PF_FAM_carry_one"}]}], "local": True, "npc_range": 60},
    ], "Every 30 seconds while you carry a baby: it stays in your arms however fast you walk.",
        recurrence="30 seconds", **{"global": True}, condition={"u_has_effect": "PF_carrying_baby"}),
    eoc("PF_FAM_carry_one", [
        # a baby whose carrier died before day 151's fix: their guardian (the living parent, or whoever took them in) carries them
        {"set_string_var": "pf_reg_<u_val:pf_carrier>_dead", "target_var": ctx("cd"), "parse_tags": True},
        {"if": {"and": [m("value_or(v_cd, 0) == 1"), m("has_var(u_pf_guardian)"), {"not": {"compare_string": [{"u_val": "pf_guardian"}, "none"]}},
                        {"not": {"compare_string": [{"u_val": "pf_guardian"}, {"u_val": "pf_carrier"}]}}]},
         "then": [{"copy_var": {"u_val": "pf_guardian"}, "target_var": {"u_val": "pf_carrier"}}]},
        {"copy_var": {"u_val": "pf_carrier"}, "target_var": g("pf_find_uid")},
        {"u_location_variable": {"u_val": "pf_pos"}},
        m("pf_find_ok = 0"), m("pf_fm_gap = 1"),
        {"if": {"not": {"compare_string": [g("pf_find_uid"), "AVATAR"]}}, "then": [m("pf_fm_gap = 4")]},
        {"if": {"compare_string": [g("pf_find_uid"), "AVATAR"]},
         "then": [{"run_eocs": {"id": "PF_FAM_carry_av", "effect": [{"u_location_variable": g("pf_fm_fpos")}]}, "alpha_talker": "avatar"},
                  {"if": {"u_has_effect": "PF_infant"}, "then": [{"run_eocs": {"id": "PF_FAM_carry_wt", "effect": [{"u_add_effect": "PF_carrying_baby", "duration": "6 minutes"}]}, "alpha_talker": "avatar"}]},
                  m("pf_find_ok = 1")],
         "else": [{"run_eocs": "PF_FIND_by_uid", "alpha_talker": "avatar"},
                  {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": {"id": "PF_FAM_carry_np", "effect": [{"u_location_variable": g("pf_fm_fpos")}]}, "alpha_talker": g("pf_find_who")}]},
                  # a band baby from before day 151 (never linked) joins its carrier's band now (a unique-id lookup, cheap;
                  # PF_FAM_band_baby_leader does nothing for a carrier who isn't in a band)
                  {"if": m("value_or(u_pf_band, 0) == 0"), "then": [
                      {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_fm_lnk_baby")}, m("pf_fm_lnk_ok = 0"),
                      {"u_run_npc_eocs": ["PF_FAM_band_baby_leader"], "unique_ids": [{"u_val": "pf_carrier"}], "local": False},
                      {"if": m("pf_fm_lnk_ok == 1"), "then": [{"run_eocs": "PF_BAND_link"}]}]}]},
        {"if": {"and": [m("pf_find_ok == 1"), m("distance(u_pf_pos, pf_fm_fpos) > pf_fm_gap")]}, "then": [
            {"copy_var": {"u_val": "pf_pos"}, "target_var": g("pf_fm_bpos")},
            m("pf_fm_bx = (pf_fm_bpos.x > pf_fm_fpos.x) - (pf_fm_bpos.x < pf_fm_fpos.x)"),
            m("pf_fm_by = (pf_fm_bpos.y > pf_fm_fpos.y) - (pf_fm_bpos.y < pf_fm_fpos.y)"),
            {"if": m("(pf_fm_bx == 0) * (pf_fm_by == 0) == 1"), "then": [m("pf_fm_bx = -1")]},
            {"location_variable_adjust": g("pf_fm_fpos"), "x_adjust": m("pf_fm_bx * (pf_fm_gap > 1 ? 2 : 1)"), "y_adjust": m("pf_fm_by * (pf_fm_gap > 1 ? 2 : 1)")},
            {"u_teleport": g("pf_fm_fpos"), "force_safe": True}]},
    ], "u = a baby being carried (u_pf_follow == 2).  Wherever the carrier goes, the baby is with them (an in-bubble move, cheap).  Carrying one yourself costs 4 kg of carry weight.  The baby lands on the carrier's side facing where it was, i.e. behind someone walking away: a fixed side (it was always east) puts it in the path, and walking into a neutral NPC attacks them (found 2026-10-11: you swung at the baby you were carrying, and it turned hostile).  An NPC carrier keeps the baby 2 tiles behind and only within 4: right beside them, the carrier shoved the baby every turn (vanilla move_away_from) and barked 'let me pass' every second.",
        condition={"and": [{"or": [{"u_has_effect": "PF_infant"}, {"u_has_effect": "PF_toddler"}]}, m("value_or(u_pf_follow, 0) == 2")]}),
    eoc("PF_FAM_partner_helps", [
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_find_uid")},
        {"run_eocs": "PF_FIND_by_uid"},
        {"u_location_variable": g("pf_fm_avpos")},
        {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_FAM_helps_one", "alpha_talker": g("pf_find_who"), "beta_talker": "avatar"}]},
    ], "u = you, pregnant past the first stage.  If the one you're with is within 8 tiles, they carry the heavy stuff: +7 kg carry weight while they're close.",
        condition={"and": [m("value_or(u_pf_preg, 0) == 1"), m("value_or(u_pf_preg_stage, 0) >= 2"), m("value_or(u_pf_has_sweet, 0) == 1")]}),
    eoc("PF_FAM_helps_one", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_fm_avpos) <= 8"), "then": [
            {"run_eocs": {"id": "PF_FAM_help_eff", "effect": [{"u_add_effect": "PF_partner_carries", "duration": "6 minutes"}]}, "alpha_talker": "avatar"},
            {"if": cooldown_ok_c("pf_help_line", "1 d"), "then": [m("pf_help_line = time('now')"), name_into("pf_say_a"), line("carry_load")]}]},
    ], "Alpha = your partner, beta = you."),
    eoc("PF_FAM_follow_one", [
        {"set_string_var": "none", "target_var": g("pf_find_uid")},
        {"copy_var": {"u_val": "pf_dad"}, "target_var": g("pf_find_uid")},
        {"if": {"not": {"compare_string": [{"u_val": "pf_mom"}, "none"]}}, "then": [{"copy_var": {"u_val": "pf_mom"}, "target_var": g("pf_find_uid")}]},
        {"if": {"not": {"compare_string": [{"u_val": "pf_guardian"}, "none"]}}, "then": [{"copy_var": {"u_val": "pf_guardian"}, "target_var": g("pf_find_uid")}]},
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": {"compare_string": [g("pf_find_uid"), "AVATAR"]},
         "then": [{"run_eocs": {"id": "PF_FAM_follow_av", "effect": [{"u_location_variable": g("pf_fm_fpos")}]}, "alpha_talker": "avatar"}, m("pf_find_ok = 1")],
         "else": [{"run_eocs": "PF_FIND_by_uid", "alpha_talker": "avatar"},
                  {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": {"id": "PF_FAM_follow_np", "effect": [{"u_location_variable": g("pf_fm_fpos")}]}, "alpha_talker": g("pf_find_who")}]}]},
        # full run day 150: at home the children trailed Dante from room to room and stood in the doorway in a column, so he
        # couldn't get through ("NPC in the way") and auto-travel kept stopping.  At home (both within 30 of it) they're safe
        # and have their own play; they follow only away from home.  Day 150: and when you went out (the expedition east) they
        # followed you past a wasp nest and a flesh-raptor fight.  A child at home stays home with the household.
        m("pf_fm_home = (value_or(pf_home_set, 0) == 1) * (distance(u_pf_pos, pf_home_loc) <= 30)"),
        # full run day 151: Taunya (16) was 15 tiles from home with no grown-up near when a skeletal dog found her; she fled
        # into open ground and died.  At home, a child with no grown-up (or you) within 10 tiles who has wandered more than 10
        # tiles from home (their family's house, if they have one) comes back in.
        {"if": {"and": [m("pf_fm_home == 1"), m("value_or(u_pf_resident, 0) == 1"), {"not": {"u_has_effect": "PF_infant"}}]}, "then": [
            {"copy_var": {"u_val": "pf_pos"}, "target_var": g("pf_fm_kpos")},
            {"run_eocs": {"id": "PF_FAM_av_pos", "effect": [{"u_location_variable": g("pf_fm_avp")}]}, "alpha_talker": "avatar"},
            m("pf_fm_adults = distance(pf_fm_avp, pf_fm_kpos) <= 10"),
            {"u_run_npc_eocs": [{"id": "PF_FAM_adult_near", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1")]},
                                 "effect": [{"u_location_variable": {"u_val": "pf_pos"}},
                                            {"if": m("distance(u_pf_pos, pf_fm_kpos) <= 10"), "then": [m("pf_fm_adults += 1")]}]}],
             "local": True, "npc_range": 40},
            {"copy_var": g("pf_home_loc"), "target_var": {"u_val": "pf_anchor"}},
            {"if": m("has_var(u_pf_house)"), "then": [{"copy_var": {"u_val": "pf_house"}, "target_var": {"u_val": "pf_anchor"}}]},
            {"if": m("(pf_fm_adults == 0) * (distance(u_pf_pos, u_pf_anchor) > 10)"), "then": [
                {"copy_var": {"u_val": "pf_anchor"}, "target_var": {"u_val": "pf_walk_to"}},
                {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("rand(4) - 2"), "y_adjust": m("rand(4) - 2")},
                {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
                m("pf_kids_called_in = value_or(pf_kids_called_in, 0) + 1")]}]},
        {"if": {"and": [m("pf_find_ok == 1"), m("pf_fm_home == 0"), m("distance(u_pf_pos, pf_fm_fpos) > 8"), {"u_has_effect": "PF_toddler"}]}, "then": [
            {"copy_var": {"u_val": "pf_pos"}, "target_var": g("pf_fm_bpos")},
            m("pf_fm_bx = (pf_fm_bpos.x > pf_fm_fpos.x) - (pf_fm_bpos.x < pf_fm_fpos.x)"),
            m("pf_fm_by = (pf_fm_bpos.y > pf_fm_fpos.y) - (pf_fm_bpos.y < pf_fm_fpos.y)"),
            {"if": m("(pf_fm_bx == 0) * (pf_fm_by == 0) == 1"), "then": [m("pf_fm_bx = -1")]},
            {"location_variable_adjust": g("pf_fm_fpos"), "x_adjust": m("pf_fm_bx"), "y_adjust": m("pf_fm_by")},
            {"u_teleport": g("pf_fm_fpos"), "force_safe": True},
            {"u_location_variable": {"u_val": "pf_pos"}},
            {"if": {"and": [cooldown_ok_c("u_pf_tired_line", "1 d"), m("value_or(pf_set_chatter, 1) == 1")]}, "then": [
                m("u_pf_tired_line = time('now')"), name_into("pf_say_a"), line("toddler_tired")]}]},
        {"if": {"and": [m("pf_find_ok == 1"), m("pf_fm_home == 0"), m("distance(u_pf_pos, pf_fm_fpos) > 5")]}, "then": [
            {"copy_var": g("pf_fm_fpos"), "target_var": {"u_val": "pf_walk_to"}},
            {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("rand(2) - 1"), "y_adjust": 1},
            {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]},
    ], "u = a child who follows their family.",
        condition={"and": [{"u_has_trait": "PF_CHILD"}, m("value_or(u_pf_follow, 0) == 1")]}),
]

# ============================================================ TEACHING (v0.4: kids learn from adults and from you)
SK = [('survival', 'how to set a snare'), ('fabrication', 'how to sharpen a knife without losing a finger'), ('cooking', "how to tell when the water's really boiling"), ('firstaid', 'how to wrap a bandage tight enough'), ('tailor', 'how to patch a hole in a jacket'), ('mechanics', 'which end of a wrench does what')]
teach_try = [m("pf_tk_k = (pf_tk_s + pf_tk_i) % 6")]
for i, (sk, how) in enumerate(SK):
    teach_try.append({"if": {"and": [m("pf_tk_k == %d" % i), m("u_skill('%s') > n_skill('%s')" % (sk, sk)), m("n_skill('%s') < 4" % sk)]},
                      "then": [m("n_skill('%s') += 1" % sk), {"set_string_var": how, "target_var": g("pf_tk_how")}, m("pf_tk_done = 1")]})
teach_try.append(m("pf_tk_i += 1"))
files["teach.json"] = [
    eoc("PF_FAM_teach_try", teach_try, "Alpha = the teacher, beta = the child.  Tries skill (pf_tk_s + pf_tk_i) mod 6: if the teacher knows it better and the child is below 4, the child goes up a level and pf_tk_how says what they learned."),
    eoc("PF_FAM_teach_do", [
        m("pf_tk_done = 0"), m("pf_tk_s = rand(5)"), m("pf_tk_i = 0"),
        {"run_eocs": "PF_FAM_teach_try", "condition": {"and": [m("pf_tk_i < 6"), m("pf_tk_done == 0")]}, "iterations": 7},
        {"if": m("pf_tk_done == 1"), "then": [
            m("n_pf_taught_t = time('now')"),
            name_into("pf_say_b"), name_into("pf_say_a", "<npc_name>"),
            {"if": m("value_or(pf_tk_quiet, 0) == 0"), "then": [{"if": "u_is_avatar", "then": [line("kid_learn_you")], "else": [line("kid_learn")]}]},
            m("pf_m_str_in = 40"), {"run_eocs": "PF_MK_taught"},
            m("pf_taught_total = value_or(pf_taught_total, 0) + 1")]},
    ], "Alpha = the teacher (an adult, or you), beta = the child.  Learning by watching and doing; a taught moment (warmth and trust both ways)."),
]

# ============================================================ KIDS' DAYS (play, chores, questions; comfort for grieving children)
def deal(used, n):
    """_p = a random one of n lines the deck in `used` (a bitmask global) hasn't dealt; a fresh deck starts with the last one out.
    Same as gen_people's deal()."""
    return ([{"if": m(f"value_or({used}, 0) >= {2 ** n - 1}"), "then": [m(f"{used} = 2 ^ value_or({used}_last, 0)")]}, m(f"_p = rand({n - 1})")]
            + [{"if": m(f"floor(value_or({used}, 0) / (2 ^ _p)) % 2 == 1"), "then": [m(f"_p = (_p + 1) % {n}")]} for _ in range(n - 1)]
            + [m(f"{used} = value_or({used}, 0) + 2 ^ _p"), m(f"{used}_last = _p")])
KQ = ["Why don't the dead ever get tired?", 'Were there really stores with nothing but shoes in them?', "What's the ocean like?", 'If we find a dog, can we keep it?', 'Why do grown-ups keep looking at the dark?', 'Did you have a mom?  What was she like?',
      'What did people do all day, before?', 'Do zombies dream?', 'Is the moon the same moon as before?', 'Why do you talk to the sky sometimes?',
      'What was your favorite food?  Like, ever?', 'Can I have a gun when I am bigger?', "Where do the birds go when it's cold?", 'Will we always live here?',
      # day 164: more questions, so the deck lasts
      'Why is the sky that color at night now?', 'Did you ever ride in an airplane?', 'Can dead people hear us?',
      'How old is the oldest person in the whole world?', 'Who decided which plants you can eat?', 'Are there other kids anywhere?',
      'What happens to the zombies in the winter?', 'Why do you always check the door twice?', 'Can you teach me to whistle with two fingers?',
      'If I was gone, would you come looking?']
q_eff = [{"if": m(f"pf_kq == {i}"), "then": [{"set_string_var": q, "target_var": g("pf_kq_text")}]} for i, q in enumerate(KQ)]
files["kids.json"] = [
    eoc("PF_FAM_kid_day_tick", [
        {"run_eocs": "PF_THREAT_scan"},
        {"if": m("pf_threat == 0"), "then": [
            m("pf_kl = 0"),
            {"u_location_variable": g("pf_fm_avpos")},
            # full run day 115: "Creola Bellamy helps you sort through a pile of junk…" while you slept.  Asleep, you're not near.
            m("pf_fm_av_awake = 1"), {"if": {"or": [{"u_has_effect": "sleep"}, {"u_has_effect": "lying_down"}]}, "then": [m("pf_fm_av_awake = 0")]},  # day 162: two questions while you lay down to sleep
            {"u_run_npc_eocs": ["PF_FAM_kid_moment"], "local": True, "npc_range": 40}]},
    ], "Every 2 hours by day (08:00-19:00), when it's calm: children live their lives: play, small chores, questions, and grief.  At most two lines each time.",
        recurrence="2 hours", **{"global": True},
        condition={"and": [m("time_since('midnight', 'unit': 'hours') >= 8"), m("time_since('midnight', 'unit': 'hours') < 19")]}),
    eoc("PF_FAM_kid_moment", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kid_uid")},
        name_into("pf_say_a"),
        {"u_location_variable": {"u_val": "pf_pos"}},
        m("pf_kid_avnear = (distance(u_pf_pos, pf_fm_avpos) <= 8) * value_or(pf_fm_av_awake, 1)"),
        # full run day 99: the morning after four of the household died, the children asked about the sky and built a fort.
        # The first time a child is around after one of ours dies (within 2 days), they notice.
        {"if": {"and": [m("time('now') - value_or(pf_loss_t, -999999) < time('2 d')"), m("value_or(u_pf_loss_seen, 0) != value_or(pf_loss_n, 0)")]},
         "then": [m("u_pf_loss_seen = pf_loss_n"), m("pf_kl += 1"),
                  {"if": m(CALM_LINES), "then": [{"if": m("value_or(pf_loss_multi, 0) == 1"), "then": [line("kid_loss_many")], "else": [line("kid_loss_one")]}]}],
         "else": [
        {"if": m("time('now') < value_or(u_pf_mourn_until, 0)"),
         "then": [{"if": m("has_var(u_pf_lost_t) * (rand(1) == 0)"), "then": [{"run_eocs": "PF_FAM_kid_grief"}], "else": [{"run_eocs": "PF_FAM_kid_comfort"}]}],
         "else": [{"run_eocs": "PF_FAM_kid_heal"}, m("_a = rand(3)"),
                  {"if": {"and": [m("_a == 3"), cooldown_ok_c("u_pf_taught_t", "1 d")]}, "then": [{"run_eocs": "PF_FAM_kid_learn"}],
                   "else": [{"if": m("_a == 3"), "then": [m("_a = rand(2)")]}]},
                  {"if": m("_a == 0"), "then": [{"run_eocs": "PF_FAM_kid_play"}]},
                  {"if": m("_a == 1"), "then": [{"run_eocs": "PF_FAM_kid_chore"}]},
                  {"if": m("_a == 2"), "then": [{"run_eocs": "PF_FAM_kid_question"}]}]}]},
    ], "u = a child (walking, not a baby).",
        condition={"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}, m("pf_kl < 2"), {"or": [m("rand(1) == 0"), m("value_or(pf_kid_force, 0) == 1")]}]}),
    eoc("PF_FAM_kid_learn", [
        m("pf_kc_found = 0"),
        {"if": m("pf_kid_avnear"), "then": [m("pf_kc_found = 2")],
         "else": [{"u_run_npc_eocs": ["PF_FAM_kid_helper_of"], "local": True, "npc_range": 15}]},
        {"if": m("pf_kc_found == 2"), "then": [m("pf_kl += 1"), {"run_eocs": "PF_FAM_teach_do", "alpha_talker": "avatar", "beta_talker": "u"}]},
        {"if": m("pf_kc_found == 1"), "then": [m("pf_kl += 1"), {"run_eocs": "PF_FAM_teach_do", "alpha_talker": g("pf_kc_who"), "beta_talker": "u"}]},
    ], "u = a child.  They pester a grown-up (you, if you're near) to show them how something works.  Once a day per child."),
    eoc("PF_FAM_kid_play", [
        m("pf_kp_found = 0"),
        {"u_run_npc_eocs": ["PF_FAM_kid_playmate"], "local": True, "npc_range": 12},
        {"if": m("pf_kp_found == 1"),
         "then": [m("pf_kl += 1"), {"if": m(CALM_LINES), "then": [{"math": ["_p = rand(5)"]}, {"if": {"math": ["_p == value_or(pf_kid_tag_last, -1)"]}, "then": [{"math": ["_p = (_p + 1) % 6"]}]}, {"math": ["pf_kid_tag_last = _p"]}, {"if": {"math": ["_p == 0"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_tag_0"}}]}, {"if": {"math": ["_p == 1"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_tag_1"}}]}, {"if": {"math": ["_p == 2"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_tag_2"}}]}, {"if": {"math": ["_p == 3"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_tag_3"}}]}, {"if": {"math": ["_p == 4"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_tag_4"}}]}, {"if": {"math": ["_p == 5"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_tag_5"}}]}]},
                  m("pf_m_str_in = 25"), {"run_eocs": "PF_MK_fire_evening", "beta_talker": g("pf_kp_who")}],
         "else": [m("pf_kl += 1"), {"if": m(CALM_LINES), "then": [{"if": m("weather('precipitation') > 0"), "then": [{"math": ["_p = rand(1)"]}, {"if": {"math": ["_p == value_or(pf_kid_wet_last, -1)"]}, "then": [{"math": ["_p = (_p + 1) % 2"]}]}, {"math": ["pf_kid_wet_last = _p"]}, {"if": {"math": ["_p == 0"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_wet_0"}}]}, {"if": {"math": ["_p == 1"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_wet_1"}}]}], "else": [{"math": ["_p = rand(7)"]}, {"if": {"math": ["_p == value_or(pf_kid_alone_last, -1)"]}, "then": [{"math": ["_p = (_p + 1) % 8"]}]}, {"math": ["pf_kid_alone_last = _p"]}, {"if": {"math": ["_p == 0"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_alone_0"}}]}, {"if": {"math": ["_p == 1"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_alone_1"}}]}, {"if": {"math": ["_p == 2"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_alone_2"}}]}, {"if": {"math": ["_p == 3"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_alone_3"}}]}, {"if": {"math": ["_p == 4"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_alone_4"}}]}, {"if": {"math": ["_p == 5"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_alone_5"}}]}, {"if": {"math": ["_p == 6"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_alone_6"}}]}, {"if": {"math": ["_p == 7"]}, "then": [{"run_eocs": "PF_SAY_family", "alpha_talker": "avatar", "variables": {"line": "kid_alone_7"}}]}]}]}]},
    ], "u = a child.  With another child near, they play together (a small bond); alone, they invent something.  Pools with no back-to-back repeats (variety pass)."),
    eoc("PF_FAM_kid_playmate", [m("pf_kp_found = 1"), name_into("pf_say_b"), {"u_set_talker": g("pf_kp_who")}],
        condition={"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}, m("pf_kp_found == 0"),
                           {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kid_uid")]}}]}),
    eoc("PF_FAM_kid_chore", [
        m("pf_kc_found = 0"),
        {"u_run_npc_eocs": ["PF_FAM_kid_helper_of"], "local": True, "npc_range": 15},
        # full run day 108: Lakia, then Aron, each "helps you sort through a pile of junk" and hands you a marble, back to
        # back.  One child's junk pile with you every 6 hours; the others tag along with another grown-up.
        {"if": {"and": [m("pf_kid_avnear"), m("time('now') - value_or(pf_kc_you_t, -999999) >= time('6 h')")]}, "then": [m("pf_kc_found = 2")]},
        {"if": m("pf_kc_found > 0"), "then": [
            m("pf_kl += 1"),
            {"if": m("pf_kc_found == 2"),
             "then": [m("pf_kc_you_t = time('now')"), {"if": m(CALM_LINES), "then": [line("kid_chore_you")]},
                      {"run_eocs": "PF_GIVE_marble", "alpha_talker": "avatar"},
                      m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_gift", "beta_talker": "avatar"}],
             # full run day 148: Lakia, then Creola "follows Mitzi Nunes around for hours", back to back.  One such line every
             # 3 hours from three versions (the others still get the moment, silently).
             "else": [{"if": {"and": [m(CALM_LINES), m("time('now') - value_or(pf_kc_line_t, -999999) >= time('3 h')")]}, "then": [
                          m("pf_kc_line_t = time('now')"),
                          m("_v = rand(2)"), {"if": m("_v == value_or(pf_kc_line_last, -1)"), "then": [m("_v = (_v + 1) % 3")]}, m("pf_kc_line_last = _v"),
                          {"if": m("_v == 0"), "then": [line("kid_chore")]}, {"if": m("_v == 1"), "then": [line("kid_chore_1")]},
                          {"if": m("_v == 2"), "then": [line("kid_chore_2")]}]},
                      m("pf_m_str_in = 25"), {"run_eocs": "PF_MK_fire_evening", "beta_talker": g("pf_kc_who")}]}]},
    ], "u = a child.  They tag along on a grown-up's chores; if you're close, it's your pile of junk, and they find you a marble."),
    eoc("PF_FAM_kid_helper_of", [m("pf_kc_found = 1"), name_into("pf_say_b"), {"u_set_talker": g("pf_kc_who")}],
        condition={"and": [ADULT, m("pf_kc_found == 0")]}),
    # full run day 80: "Why do grown-ups keep looking at the dark?" from two children six hours apart; a deck (gen_people deal())
    # full run day 164: "Is the moon the same moon as before?" from Lakia and then Creola, a day apart.  Every child's question
    # turn drew a card, heard or not, so the deck went round in about a day.  Only a question someone hears is dealt.
    eoc("PF_FAM_kid_question", [
        m("pf_kc_found = 0"),
        {"if": m("pf_kid_avnear"), "then": [m("pf_kc_found = 2")],
         "else": [{"u_run_npc_eocs": ["PF_FAM_kid_helper_of"], "local": True, "npc_range": 15}]},
        {"if": m("pf_kc_found > 0"), "then": deal("pf_kq_used", len(KQ)) + [m("pf_kq = _p")] + q_eff},
        {"if": m("pf_kc_found == 2"), "then": [m("pf_kl += 1"), {"if": m(CALM_LINES), "then": [line("kid_ask_you")]},
                                             m("pf_m_str_in = 25"), {"run_eocs": "PF_MK_memory_recalled", "beta_talker": "avatar"}]},
        {"if": m("pf_kc_found == 1"), "then": [m("pf_kl += 1"), {"if": m(CALM_LINES), "then": [line("kid_ask")]},
                                             m("pf_m_str_in = 25"), {"run_eocs": "PF_MK_fire_evening", "beta_talker": g("pf_kc_who")}]},
    ], "u = a child.  They ask you (if you're near) or a grown-up one of the questions children ask."),
    eoc("PF_FAM_kid_grief", [
        m("pf_kl += 1"),
        {"copy_var": {"u_val": "pf_lost_name"}, "target_var": g("pf_say_b")},
        {"set_string_var": "the grown-ups", "target_var": g("pf_say_c")},
        {"if": m("has_var(u_pf_guard_name)"), "then": [{"copy_var": {"u_val": "pf_guard_name"}, "target_var": g("pf_say_c")}]},
        m("_p = rand(3)"), {"if": m("_p == value_or(pf_kg_last, -1)"), "then": [m("_p = (_p + 1) % 4")]}, m("pf_kg_last = _p"),
        {"if": m(CALM_LINES), "then": [{"if": m(f"_p == {i}"), "then": [line(f"kid_grief_{i}")]} for i in range(4)]},
    ], "u = a child mourning a parent or guardian (v0.7).  A line of their own, by name: who they lost and who looks after them now."),
    eoc("PF_FAM_kid_heal", [
        m("u_pf_lost_healed = 1"), m("pf_kl += 1"),
        {"if": m("value_or(u_pf_guard_you, 0) == 1"),
         "then": [{"if": m(CALM_LINES), "then": [line("kid_heal_you")]}, m("pf_m_str_in = 70"), {"run_eocs": "PF_MK_care_given", "alpha_talker": "avatar", "beta_talker": "u"}],
         "else": [m("pf_find_ok = 0"),
                  {"if": m("has_var(u_pf_guardian)"), "then": [{"copy_var": {"u_val": "pf_guardian"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"}]},
                  {"if": m("pf_find_ok == 1"),
                   "then": [{"copy_var": {"u_val": "pf_guard_name"}, "target_var": g("pf_say_b")},
                            {"if": m(CALM_LINES), "then": [line("kid_heal")]}, m("pf_m_str_in = 70"), {"run_eocs": "PF_MK_care_given", "alpha_talker": g("pf_find_who"), "beta_talker": "u"}],
                   "else": [{"if": m(CALM_LINES), "then": [line("kid_heal_alone")]}]}]},
    ], "u = a child whose mourning just ended (v0.7).  A first real laugh, and a strong bond to whoever stayed (care, 70).",
        condition={"and": [m("has_var(u_pf_lost_t)"), m("value_or(u_pf_lost_healed, 0) == 0"), m("time('now') >= value_or(u_pf_mourn_until, 0)")]}),
    eoc("PF_FAM_kid_comfort", [
        m("pf_fm_best = -1"),
        {"u_run_npc_eocs": ["PF_FAM_comforter"], "local": True, "npc_range": 15},
        m("pf_kl += 1"),
        {"if": m("pf_fm_best >= 0"),
         "then": [{"run_eocs": "PF_FAM_comfort_do", "alpha_talker": g("pf_fm_carer"), "beta_talker": "u"}],
         "else": [{"if": m(CALM_LINES), "then": [line("kid_alone_grief")]}]},
    ], "u = a grieving child.  An adult who cares sits with them (a day less of mourning); with nobody, they sit alone."),
    eoc("PF_FAM_comforter", [
        {"copy_var": g("pf_kid_uid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        m("_score = pf_read_w + (u_has_trait('PF_Q_MOTHER_HEN') ? 20 : 0)"),
        {"if": {"and": [m("_score >= 10"), m("_score > pf_fm_best")]}, "then": [m("pf_fm_best = _score"), {"u_set_talker": g("pf_fm_carer")}]},
    ], condition=ADULT),
    eoc("PF_FAM_comfort_do", [
        name_into("pf_say_a"), name_into("pf_say_b", "<npc_name>"),
        m("n_pf_mourn_until = max(time('now'), value_or(n_pf_mourn_until, 0) - time('1 d'))"),
        # full run day 124: five of these from Mitzi in one afternoon (four grieving children).  The comfort still works every
        # time; the line is said once every 4 hours, in turn from three.
        {"if": {"and": [m(CALM_LINES), m("time('now') - value_or(pf_kcom_t, -999999) >= time('4 h')")]}, "then": [
            m("pf_kcom_t = time('now')"), m("pf_kcom_rot = (value_or(pf_kcom_rot, -1) + 1) % 3"),
            {"if": m("pf_kcom_rot == 0"), "then": [line("kid_comforted")]},
            {"if": m("pf_kcom_rot == 1"), "then": [line("kid_comforted_1")]},
            {"if": m("pf_kcom_rot == 2"), "then": [line("kid_comforted_2")]}]},
        m("pf_m_str_in = 45"), {"run_eocs": "PF_MK_care_given"},
    ], "Alpha = the adult, beta = the grieving child."),
]

# ============================================================ ORPHANS & ADOPTION (the gap v0.2's tests surfaced)
files["orphans.json"] = [
    eoc("PF_FAM_on_parent_death", [
        # v0.7: who they lost, by name (talk, grief lines, the day it lifts); only for a parent or guardian, not a band leader
        {"if": {"or": [{"compare_string": [{"u_val": "pf_mom"}, g("pf_dead_uid")]}, {"compare_string": [{"u_val": "pf_dad"}, g("pf_dead_uid")]},
                       {"compare_string": [{"u_val": "pf_guardian"}, g("pf_dead_uid")]}]},
         "then": [{"copy_var": g("pf_dead_name"), "target_var": {"u_val": "pf_lost_name"}}, m("u_pf_lost_t = time('now')"), m("u_pf_lost_healed = 0"),
                  m("u_pf_mourn_until = max(value_or(u_pf_mourn_until, 0), time('now') + time('14 d'))")]},
        {"if": {"compare_string": [{"u_val": "pf_guardian"}, g("pf_dead_uid")]}, "then": [{"set_string_var": "none", "target_var": {"u_val": "pf_guardian"}}]},
        # v0.7: a living parent keeps them (losing their mother made a child an orphan with their father standing there, and an NPC could take in your own child)
        {"set_string_var": "none", "target_var": g("pf_fm_other")},
    ] + [{"if": {"and": [m(f"has_var(u_pf_{p})"), {"not": {"compare_string": [{"u_val": f"pf_{p}"}, "none"]}}, {"not": {"compare_string": [{"u_val": f"pf_{p}"}, g("pf_dead_uid")]}},
                         {"compare_string": [g("pf_fm_other"), "none"]}]},
          "then": [{"set_string_var": f"pf_reg_<u_val:pf_{p}>_dead", "target_var": ctx("od"), "parse_tags": True},
                   {"if": m("value_or(v_od, 0) == 0"), "then": [{"copy_var": {"u_val": f"pf_{p}"}, "target_var": g("pf_fm_other")}]}]} for p in ("mom", "dad")] + [
        {"if": {"not": {"compare_string": [g("pf_fm_other"), "none"]}},
         "then": [m("u_pf_needs_home = 0"), m("u_pf_orphaned = 0"),
                  {"copy_var": g("pf_fm_other"), "target_var": {"u_val": "pf_guardian"}},
                  # day 151: Golly died and her newborn's carrier stayed Golly; nobody carried Marylin.  The living parent does.
                  {"if": {"and": [m("value_or(u_pf_follow, 0) == 2"), {"compare_string": [{"u_val": "pf_carrier"}, g("pf_dead_uid")]}]},
                   "then": [{"copy_var": g("pf_fm_other"), "target_var": {"u_val": "pf_carrier"}}]},
                  {"if": {"compare_string": [g("pf_fm_other"), "AVATAR"]},
                   "then": [m("u_pf_guard_you = 1"), {"set_string_var": "you", "target_var": {"u_val": "pf_guard_name"}}],
                   "else": [m("u_pf_guard_you = 0"),
                            {"set_string_var": "pf_name_<global_val:pf_fm_other>", "target_var": ctx("on"), "parse_tags": True},
                            {"copy_var": {"var_val": "on"}, "target_var": {"u_val": "pf_guard_name"}}]}],
         "else": [m("u_pf_needs_home = 1"), m("u_pf_orphaned = 1"),
                  {"run_eocs": "PF_THREAT_scan", "alpha_talker": "avatar"},
                  {"if": m("pf_threat == 0"), "then": [{"run_eocs": "PF_FAM_find_home"}]}]},
    ], "u = a child whose parent or guardian just died (called from hearts grief).  v0.7: a living parent keeps them; they remember who they lost (pf_lost_name).  Children mourn twice as long, and the adults around them decide who takes them in, once it's calm (the playtest had Yetta comforting the babies while the zombie was still there); otherwise the 2-hourly orphan check does it later.",
        condition={"u_has_trait": "PF_CHILD"}),
    eoc("PF_FAM_parent_check", [{"run_eocs": "PF_FAM_on_parent_death"}],
        "u = someone who outlived pf_dead_uid (called for every survivor from PF_GRIEF_one).  If they're a child and the dead was their parent, guardian or band leader, they're an orphan now.",
        condition={"and": [{"u_has_trait": "PF_CHILD"},
                           {"or": [{"compare_string": [{"u_val": "pf_mom"}, g("pf_dead_uid")]}, {"compare_string": [{"u_val": "pf_dad"}, g("pf_dead_uid")]},
                                   {"compare_string": [{"u_val": "pf_guardian"}, g("pf_dead_uid")]}, {"compare_string": [{"u_val": "pf_leader"}, g("pf_dead_uid")]}]}]}),
    eoc("PF_FAM_find_home", [
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_fm_kid")},
        m("pf_fm_best = -1"),
        {"u_run_npc_eocs": ["PF_FAM_home_cand"], "local": True, "npc_range": 30},
        {"if": m("pf_fm_best >= 0"), "then": [{"run_eocs": "PF_FAM_adopt", "alpha_talker": g("pf_fm_carer"), "beta_talker": "u"}]},
    ], "u = a child who needs a home.  Every adult nearby weighs in from their own view of the child; the one who cares most takes them in (warmth plus mother hen +20, loyal +10).  Needs warmth 10: strangers walk past.",
        condition=m("value_or(u_pf_needs_home, 0) == 1")),
    eoc("PF_FAM_home_cand", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": g("pf_fm_kid"), "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("_score = pf_read_w"),
        {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("_score += 20")]},
        {"if": {"u_has_trait": "PF_Q_LOYAL"}, "then": [m("_score += 10")]},
        {"if": {"and": [m("_score >= 10"), m("_score > pf_fm_best"), m("time('now') >= value_or(u_pf_mourn_until, 0) - time('10 d')"),
                        {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_dead_uid")]}}]},
         "then": [m("pf_fm_best = _score"), {"u_set_talker": g("pf_fm_carer")}]},
    ], "u = an adult near the orphan.", condition=ADULT),
    eoc("PF_FAM_adopt", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"npc_val": "pf_guardian"}},
        {"if": "u_is_avatar", "then": [m("n_pf_guard_you = 1"), {"set_string_var": "you", "target_var": {"npc_val": "pf_guard_name"}}],
         "else": [m("n_pf_guard_you = 0"), {"set_string_var": "<u_name>", "target_var": {"npc_val": "pf_guard_name"}, "parse_tags": True}]},
        m("n_pf_needs_home = 0"), m("n_pf_orphaned = 0"), m("n_pf_follow = 1"), m("n_pf_is_leader = 0"),
        {"if": {"npc_has_effect": "PF_infant"}, "then": [m("n_pf_follow = 2"), {"copy_var": {"u_val": "pf_uid"}, "target_var": {"npc_val": "pf_carrier"}}]},
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_fm_kid")},
    ] + regcopy("pf_fm_kid", "gd", {"u_val": "pf_uid"}) + [
        {"run_eocs": "PF_FAM_list_kid", "alpha_talker": "npc"},
        m("u_pf_kids_n = value_or(u_pf_kids_n, 0) + 1"),
        name_into("pf_say_a"), name_into("pf_say_b", "<npc_name>"),
        # full run: a child 18 tiles off "took your hand"; one further than a few steps is called over and comes running
        {"if": "u_is_avatar", "then": [
            {"u_location_variable": g("pf_fm_av_at")}, {"npc_location_variable": g("pf_fm_kid_at")},
            {"if": m("distance(pf_fm_av_at, pf_fm_kid_at) > 3"), "then": [
                {"copy_var": g("pf_fm_av_at"), "target_var": {"npc_val": "pf_walk_to"}},
                {"location_variable_adjust": {"npc_val": "pf_walk_to"}, "x_adjust": 1},
                {"run_eocs": {"id": "PF_FAM_adopt_come", "effect": [{"u_set_guard_pos": {"u_val": "pf_walk_to"}}]}, "alpha_talker": "npc"},
                line("adopt_you_far")],
             "else": [line("adopt_you")]}], "else": [line("adopt_npc")]},
        m("pf_m_str_in = 80"), {"run_eocs": "PF_MK_adopted"},
        m("pf_adoptions_total = value_or(pf_adoptions_total, 0) + 1"),
    ], "Alpha = the adult, beta = the child.  The child follows their guardian from now on, leaves A-Life band control (u_pf_is_leader = 0), and both remember it (adopted: strength 80)."),
    eoc("PF_FAM_list_kid", [
        {"if": {"not": m("has_var(u_pf_born_t)")}, "then": [
            m("u_pf_born_t = time('now') - time('1 d') * 364 * u_val('age') / %s" % PACE), m("u_pf_kid_stage = 1"),
            {"if": {"not": m("has_var(u_pf_mom)")}, "then": [{"set_string_var": "none", "target_var": {"u_val": "pf_mom"}}, {"set_string_var": "none", "target_var": {"u_val": "pf_dad"}}]},
            m("pf_fm_ki = value_or(pf_kids_n, 0) % 30"),
            {"set_string_var": "pf_kid_<global_val:pf_fm_ki>", "target_var": ctx("kr"), "parse_tags": True},
            {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "kr"}},
            m("pf_kids_n = value_or(pf_kids_n, 0) + 1")]},
    ], "u = a child just taken in who wasn't born into our system (e.g. an A-Life band's child): gets a birth time that matches their age, and is listed for growing up.  Only A-Life persons (unique ids) can be reached by the growth tick."),
    eoc("PF_FAM_orphan_tick", [
        {"u_run_npc_eocs": ["PF_FAM_orphan_check"], "local": True, "npc_range": 60},
    ], "Every 2 hours: orphaned children in the bubble who still need a home (including children orphaned before v0.3) look for one.",
        recurrence="2 hours", **{"global": True}),
    eoc("PF_FAM_orphan_check", [
        m("pf_fm_gdead = 0"),
        {"if": m("has_var(u_pf_guardian)"), "then": [
            {"set_string_var": "pf_reg_<u_val:pf_guardian>_dead", "target_var": ctx("gdd"), "parse_tags": True},
            {"if": m("value_or(v_gdd, 0) == 1"), "then": [m("pf_fm_gdead = 1"), {"set_string_var": "none", "target_var": {"u_val": "pf_guardian"}}]}]},
        {"if": {"and": [{"or": [m("value_or(u_pf_needs_home, 0) == 1"), m("value_or(u_pf_orphaned, 0) == 1"), m("pf_fm_gdead == 1")]},
                        {"or": [m("has_var(u_pf_guardian) == 0"), {"compare_string": [{"u_val": "pf_guardian"}, "none"]}]}]},
         "then": [m("u_pf_needs_home = 1"), {"run_eocs": "PF_FAM_find_home"}]},
    ], "u = a child in the bubble.  Needs a home if orphaned, flagged, or if whoever took them in has since died.",
        condition={"u_has_trait": "PF_CHILD"}),
    eoc("PF_FAM_you_pick_up", [
        m("n_pf_follow = 2"), {"set_string_var": "AVATAR", "target_var": {"npc_val": "pf_carrier"}},
        {"u_add_effect": "PF_carrying_baby", "duration": "6 minutes"},
        name_into("pf_say_a", "<npc_name>"), line("pick_up"),
        m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_parenting"},
    ], "u = you, npc = a baby (People menu: Pick them up).  They're carried by you until you set them down or hand them over."),
    eoc("PF_FAM_you_set_down", [
        m("n_pf_follow = 0"), {"set_string_var": "none", "target_var": {"npc_val": "pf_carrier"}},
        {"u_lose_effect": "PF_carrying_baby"},
        m("pf_find_ok = 0"),
        {"if": {"not": {"compare_string": [{"npc_val": "pf_mom"}, "AVATAR"]}}, "then": [
            {"copy_var": {"npc_val": "pf_mom"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
            {"if": m("pf_find_ok == 1"), "then": [m("n_pf_follow = 2"), {"copy_var": {"npc_val": "pf_mom"}, "target_var": {"npc_val": "pf_carrier"}}]}]},
        # day 153: Marylin's mother and father were both dead and Consuelo had taken her in; the guardian takes the baby back
        {"if": {"and": [m("pf_find_ok == 0"), m("has_var(n_pf_guardian)"), {"not": {"compare_string": [{"npc_val": "pf_guardian"}, "none"]}},
                        {"not": {"compare_string": [{"npc_val": "pf_guardian"}, "AVATAR"]}}]}, "then": [
            {"copy_var": {"npc_val": "pf_guardian"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
            {"if": m("pf_find_ok == 1"), "then": [m("n_pf_follow = 2"), {"copy_var": {"npc_val": "pf_guardian"}, "target_var": {"npc_val": "pf_carrier"}}]}]},
        name_into("pf_say_a", "<npc_name>"),
        # full run day 151: Dante found Golly Whitmore's newborn alone in the grass, carried her an hour to the band, and got
        # "You hand Marylin Whitmore back to their mother."  For a mother who isn't one of yours, that's a moment.
        m("pf_fm_hb_res = 1"),
        {"if": m("(n_pf_follow == 2) * (pf_find_ok == 1)"), "then": [
            {"run_eocs": {"id": "PF_FAM_handback_mom", "effect": [name_into("pf_say_b"), m("pf_fm_hb_res = value_or(u_pf_resident, 0)")]},
             "alpha_talker": g("pf_find_who")}]},
        {"if": m("n_pf_follow == 2"),
         "then": [{"if": m("pf_fm_hb_res == 0"),
                   "then": [line("hand_back_stranger"), m("pf_m_str_in = 70"),
                            {"run_eocs": "PF_MK_care_given", "alpha_talker": "avatar", "beta_talker": g("pf_find_who")}],
                   "else": [line("hand_back")]}],
         "else": [line("set_down")]},
    ], "u = you, npc = the baby you carry (People menu: Set them down).  Their mother takes them back if she's around; otherwise they stay where you put them.  A mother who doesn't live with you counts it as care from you (70)."),
    eoc("PF_FAM_you_take_hand", [
        m("n_pf_follow = 2"), {"set_string_var": "AVATAR", "target_var": {"npc_val": "pf_carrier"}},
        name_into("pf_say_a", "<npc_name>"), line("take_hand"),
        m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_parenting"},
    ], "u = you, npc = a toddler (People menu: Take their hand).  They stay at your side until you let go."),
    eoc("PF_FAM_you_let_go", [
        m("n_pf_follow = 1"), {"set_string_var": "none", "target_var": {"npc_val": "pf_carrier"}},
        name_into("pf_say_a", "<npc_name>"), line("let_go"),
    ], "u = you, npc = the toddler whose hand you hold.  Back to following their family."),
    eoc("PF_FAM_you_teach", [
        m("pf_tk_done = 0"), m("pf_tk_s = rand(%d)" % 5), m("pf_tk_i = 0"),
        {"if": {"not": cooldown_ok_c("n_pf_taught_t", "1 d")}, "then": [m("pf_tk_i = 6")]},
        {"run_eocs": "PF_FAM_teach_try", "condition": {"and": [m("pf_tk_i < 6"), m("pf_tk_done == 0")]}, "iterations": 7},
        {"if": m("pf_tk_done == 1"),
         "then": [m("n_pf_taught_t = time('now')"), name_into("pf_say_a", "<npc_name>"), line("teach_you")],
         "else": [name_into("pf_say_a", "<npc_name>"), line("teach_none")]},
    ], "u = you, npc = a child (People menu: Teach them something).  You show them something you know better than they do (survival, fabrication, cooking, first aid, tailoring or mechanics), once a day per child, up to level 4."),
    eoc("PF_ENGINE_name_baby", [], "u = a newborn, pf_fm_mom / pf_fm_dad = the parents.  Stock build: the baby keeps the name the game gave it.  The People First Engine mod overrides this: you name your own baby (family name from you), and an NPC couple's baby takes its mother's surname."),
    eoc("PF_ENGINE_name_adoptee", [], "u = you, npc = the child you just took in.  Stock build: they keep their name.  The People First Engine mod overrides this with a naming prompt."),
    eoc("PF_FAM_you_take_in", [
        {"run_eocs": "PF_ID_ensure"},
        {"run_eocs": "PF_FAM_adopt", "beta_talker": "npc"},
        {"run_eocs": "PF_ENGINE_name_adoptee", "beta_talker": "npc"},
    ], "u = you, npc = an orphan (People menu: Take them in)."),
]

# ============================================================ LINES
LINES = {
    "preg_npc":   ("<global_val:pf_say_a> has been sick every morning for a week.  Then the news goes around the camp: <global_val:pf_say_a> is pregnant, and <global_val:pf_say_b> can't stop smiling.", "good"),
    "preg_you":   ("You've been sick every morning for a week.  You're pregnant.", "good"),
    "birth_npc":  ("It's a long night, and nobody sleeps.  By morning <global_val:pf_say_a> is holding a newborn, <global_val:pf_fm_babyname>, and the whole camp crowds in to see.", "good"),
    "birth_npc_away": ("There's a new face at home.  <global_val:pf_say_a> had the baby while you were gone: <global_val:pf_fm_babyname>.  Somebody puts the baby in your arms before you've even set your pack down.", "good"),
    "birth_npc_day": ("Hours of it, everyone pacing, nobody able to sit still.  Then a thin, furious cry: <global_val:pf_say_a> is holding a newborn, <global_val:pf_fm_babyname>, and the whole camp crowds in to see.", "good"),
    "birth_you_day": ("Hours of it, and everyone stays.  Then it's over, and you're holding <global_val:pf_fm_babyname>.", "good"),
    "birth_you":  ("It's a long night, and everyone stays.  By morning you're holding <global_val:pf_fm_babyname>.", "good"),
    "baby_rock":  ("<global_val:pf_say_a> rocks <global_val:pf_say_b> until they settle.", "info"),
    "baby_feed":  ("<global_val:pf_say_a> warms something for <global_val:pf_say_b> and feeds them, slowly, a spoonful at a time.", "info"),
    "baby_sing":  ("<global_val:pf_say_a> hums something old and tuneless until <global_val:pf_say_b> falls asleep.", "info"),
    "baby_for_you": ("<global_val:pf_say_a> takes <global_val:pf_say_b> for a while so you can rest.", "good"),
    "first_steps": ("<global_val:pf_say_a> is walking now, and following the grown-ups everywhere.", "good"),
    "grown_up":   ("<global_val:pf_say_a> isn't a child anymore.", "good"),
    "grown_up_1": ("Somebody notices <global_val:pf_say_a> is taller than them now.  When did that happen?  <global_val:pf_say_a> isn't a child anymore.", "good"),
    "grown_up_2": ("<global_val:pf_say_a> takes a turn at the grown-ups' work today and nobody sends them off.  They're not a child anymore.", "good"),
    "grown_up_yours_0": ("You look up and <global_val:pf_say_a> is looking back at you, eye to eye.  Your child isn't a child anymore.", "good"),
    "grown_up_yours_1": ("<global_val:pf_say_a> asks you something, grown-up to grown-up, and waits for a real answer.  Your kid's grown.", "good"),
    "grown_up_yours_2": ("<global_val:pf_say_a> checks the gate before bed, the way you always do.  Somewhere along the way your child grew up.", "good"),
    "crave_alone": ("You'd do terrible things for something sweet right now.", "info"),
    "crave_brought": ("<global_val:pf_say_a> turns up with <global_val:pf_say_b>.  \"Don't ask where I found it.\"", "good"),
    "carry_load": ("<global_val:pf_say_a> takes the heavy pack off your back without asking.", "good"),
    "kid_tag":    ("<global_val:pf_say_a> and <global_val:pf_say_b> play tag around the place, shrieking, until someone tells them to keep it down.", "info"),
    "kid_alone_play": ("<global_val:pf_say_a> plays some game only they understand, with three rocks and a stick.", "info"),
    "kid_chore":  ("<global_val:pf_say_a> follows <global_val:pf_say_b> around for hours, carrying things that don't need carrying.", "info"),
    "kid_chore_1": ("<global_val:pf_say_a> spends a good while at <global_val:pf_say_b>'s elbow, asking what everything is for.", "info"),
    "kid_chore_2": ("<global_val:pf_say_a> insists on helping <global_val:pf_say_b>, and is allowed to hold the important end of things.", "info"),
    "kid_chore_you": ("<global_val:pf_say_a> helps you sort through a pile of junk, and proudly hands you a marble they found.", "good"),
    "kid_ask":    ("<global_val:pf_say_a> asks <global_val:pf_say_b>, \"<global_val:pf_kq_text>\"  <global_val:pf_say_b> makes something up.", "info"),
    "kid_loss_one": ("<global_val:pf_say_a> keeps glancing at <global_val:pf_loss_name>'s place by the fire, as if they might still come back.", "info"),
    "kid_loss_many": ("<global_val:pf_say_a> counts the bedrolls twice, gets a different number than yesterday, and stops counting.", "info"),
    "kid_ask_you": ("<global_val:pf_say_a> tugs at your sleeve.  \"<global_val:pf_kq_text>\"", "info"),
    'kid_tag_0': ('<global_val:pf_say_a> and <global_val:pf_say_b> play tag around the place, shrieking, until someone tells them to keep it down.', 'info'),
    'kid_tag_1': ('<global_val:pf_say_a> and <global_val:pf_say_b> play hide and seek.  <global_val:pf_say_b> hides in the same spot every time, and <global_val:pf_say_a> pretends not to know.', 'info'),
    'kid_tag_2': ('<global_val:pf_say_a> and <global_val:pf_say_b> play zombies and survivors.  Everyone wants to be the zombie.', 'info'),
    'kid_tag_3': ('<global_val:pf_say_a> and <global_val:pf_say_b> trade treasures: a bottle cap, a feather, a key to nothing.  The negotiations take an hour.', 'info'),
    'kid_tag_4': ("<global_val:pf_say_a> and <global_val:pf_say_b> build a fort out of boards and a tarp, and won't let any grown-ups in.", 'info'),
    'kid_tag_5': ('<global_val:pf_say_a> and <global_val:pf_say_b> fall out over the rules of a game they made up, and make up again within the hour.', 'info'),
    'kid_alone_0': ('<global_val:pf_say_a> plays some game only they understand, with three rocks and a stick.', 'info'),
    'kid_alone_1': ('<global_val:pf_say_a> draws in the dirt with a stick: a house, a dog, a lot of people holding hands.', 'info'),
    'kid_alone_2': ('<global_val:pf_say_a> has a long, serious conversation with a beetle.', 'info'),
    'kid_alone_3': ('<global_val:pf_say_a> practices cartwheels until they get one right, then looks round to see if anyone saw.', 'info'),
    'kid_alone_4': ('<global_val:pf_say_a> lines up every empty can they can find and knocks them down with pebbles.', 'info'),
    'kid_alone_5': ("<global_val:pf_say_a> makes a zombie trap out of string and a pot.  It catches a grown-up's ankle twice.", 'info'),
    'kid_alone_6': ("<global_val:pf_say_a> sings a song they're making up as they go.  It's mostly about lunch.", 'info'),
    'kid_alone_7': ("<global_val:pf_say_a> 'reads' a picture book aloud to nobody, turning the pages very carefully.", 'info'),
    'kid_wet_0': ('<global_val:pf_say_a> jumps in every puddle, one after another, with great seriousness.', 'info'),
    'kid_wet_1': ('<global_val:pf_say_a> sits in the doorway catching raindrops on their tongue.', 'info'),
    "kid_grief_0": ("<global_val:pf_say_a> asks <global_val:pf_say_c> whether <global_val:pf_say_b> can see them from where they are now.  The answer takes a long time.", "info"),
    "kid_grief_1": ("<global_val:pf_say_a> carries something of <global_val:pf_say_b>'s everywhere today, and won't let anyone else hold it.", "info"),
    "kid_grief_2": ("<global_val:pf_say_a> sets out a bowl for <global_val:pf_say_b> at supper, remembers, and takes it away again before anyone can say anything.", "bad"),
    "kid_grief_3": ("<global_val:pf_say_a> won't let <global_val:pf_say_c> out of their sight today.", "info"),
    "kid_heal": ("<global_val:pf_say_a> laughs at something <global_val:pf_say_b> says, a real laugh, and then looks surprised at themselves.", "good"),
    "kid_heal_you": ("<global_val:pf_say_a> laughs at something you say, a real laugh, and then looks surprised at themselves.", "good"),
    "kid_heal_alone": ("<global_val:pf_say_a> laughs at something, a real laugh, and then looks surprised at themselves.", "good"),
    "kid_alone_grief": ("<global_val:pf_say_a> sits by themselves, hugging their knees.", "bad"),
    "kid_comforted": ("<global_val:pf_say_a> sits down next to <global_val:pf_say_b> and doesn't say anything.  After a while, <global_val:pf_say_b> leans against them.", "good"),
    "kid_comforted_1": ("<global_val:pf_say_a> finds <global_val:pf_say_b> a job to do, something small, and does it alongside them for hours.", "good"),
    "kid_comforted_2": ("<global_val:pf_say_a> tells <global_val:pf_say_b> a long, silly story about nothing.  <global_val:pf_say_b> doesn't laugh, but stays to hear the end.", "good"),
    "pick_up":    ("You pick up <global_val:pf_say_a>.  Heavier than they look.", "info"),
    "set_down":   ("You set <global_val:pf_say_a> down somewhere safe.", "info"),
    "hand_back":  ("You hand <global_val:pf_say_a> back to <global_val:pf_say_b>.", "info"),
    "hand_back_stranger": ("<global_val:pf_say_b> takes <global_val:pf_say_a> from you and holds on for a long moment before saying anything at all.", "good"),
    "big_kid":    ("<global_val:pf_say_a> doesn't want to hold anyone's hand anymore.  They're big now, they say.", "info"),
    "toddler_tired": ("<global_val:pf_say_a> has had enough walking for one day, and gets carried the rest of the way.", "info"),
    "take_hand":  ("You take <global_val:pf_say_a>'s hand.  They hold on tight.", "good"),
    "let_go":     ("You let go of <global_val:pf_say_a>'s hand, and they trot off after their family.", "info"),
    "teach_you":  ("You show <global_val:pf_say_a> <global_val:pf_tk_how>.  They get it on the third try, and look very pleased with themselves.", "good"),
    "teach_none": ("You try to show <global_val:pf_say_a> something, but there's nothing you know that they don't already, or they're tired of lessons today.", "info"),
    "kid_learn":  ("<global_val:pf_say_b> shows <global_val:pf_say_a> <global_val:pf_tk_how>.  <global_val:pf_say_a> doesn't stop talking about it all day.", "good"),
    "kid_learn_you": ("<global_val:pf_say_a> won't stop asking, so you show them <global_val:pf_tk_how>.  They get it faster than you did.", "good"),
    "adopt_npc":  ("<global_val:pf_say_a> crouches next to <global_val:pf_say_b>.  \"Hey.  You're with me now.  Okay?\"", "good"),
    "adopt_you":  ("<global_val:pf_say_b> takes your hand and doesn't let go.", "good"),
    "adopt_you_far": ("You call <global_val:pf_say_b> over.  They come running, and take your hand, and don't let go.", "good"),
}
files["lines.json"] = [eoc("PF_SAY_family", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  v0.3 lines, picked by the context var 'line'.")]

# ============================================================ FAMILY LAB
FL = []
def nearest(cond, rng=6):
    return [m("pf_ll_kd = 99"), {"u_location_variable": g("pf_ll_kav")},
            {"u_run_npc_eocs": [{"id": "PF_FL_near_%d" % len(FL), "condition": cond, "effect": [
                {"u_location_variable": {"u_val": "pf_pos"}},
                {"if": m("distance(u_pf_pos, pf_ll_kav) < pf_ll_kd"), "then": [m("pf_ll_kd = distance(u_pf_pos, pf_ll_kav)"), {"u_set_talker": g("pf_ll_kwho")}]}]}],
             "local": True, "npc_range": rng}]
FL.append(("PF_FL_expect", "Pregnancy: the nearest woman with a partner is expecting",
           "The nearest adult woman who is with a man conceives now (you count too, if you're a woman with a partner).  The news comes at the next daily step.",
           [m("pf_fl_ok = 0"),
            # you count first; if your partner isn't a man, the nearest woman who is with one (v0.7 lab test: it stopped at you)
            {"if": {"and": [m("u_gender() == 0"), m("value_or(u_pf_has_sweet, 0) == 1"), m("value_or(u_pf_preg, 0) == 0")]},
             "then": [{"run_eocs": "PF_FL_expect_one"}]},
            {"if": m("pf_fl_ok == 0"),
             "then": nearest({"and": [m("u_gender() == 0"), m("value_or(u_pf_has_sweet, 0) == 1"), m("value_or(u_pf_preg, 0) == 0"), ADULT]}) + [
                 {"if": m("pf_ll_kd < 99"), "then": [{"run_eocs": "PF_FL_expect_one", "alpha_talker": g("pf_ll_kwho")}]}]},
            {"if": m("pf_fl_ok == 1"), "then": [say("[family lab] Someone is expecting.")],
             "else": [say("[family lab] No woman with a man as partner within 6 tiles (you count first).")]}]))
FL.append(("PF_FL_expect_one", None, None, [
    {"set_string_var": "pf_reg_<u_val:pf_sweet>_g", "target_var": ctx("dg"), "parse_tags": True},
    {"if": m("value_or(v_dg, 0) != 1"), "then": [{"run_eocs": "PF_FL_noop"}], "else": [{"run_eocs": "PF_FL_expect_do"}]}]))
FL.append(("PF_FL_noop", None, None, [m("pf_fl_ok = 0")]))
FL.append(("PF_FL_expect_do", None, None, [
    m("pf_fl_ok = 1"), m("u_pf_preg = 1"), m("u_pf_preg_t = time('now')"), m("u_pf_preg_stage = 0"), m("u_pf_preg_known = 0"),
    {"copy_var": {"u_val": "pf_sweet"}, "target_var": {"u_val": "pf_preg_father"}}, {"run_eocs": "PF_FAM_track_mother"}]))
FL.append(("PF_FL_step", "Pregnancy: run the daily step now (news, stage, birth)", "Runs the pregnancy step for every expecting mother.", [{"run_eocs": "PF_FAM_preg_tick"}]))
FL.append(("PF_FL_due", "Pregnancy: everyone expecting is due now", "Moves every pregnancy to term, then runs the step: births happen if the mother is nearby.",
           [m("pf_fl_frac = 1.05"), m("pf_fl_k = 0"), {"run_eocs": "PF_FL_due_k", "condition": m("pf_fl_k < min(value_or(pf_moms_n, 0), 12)"), "iterations": 13}, {"run_eocs": "PF_FAM_preg_tick"},
            say("[family lab] Mothers due but away from you (the birth waits until they're near): <global_val:pf_fm_waiting>.")]))
FL.append(("PF_FL_due_k", None, None, [
    {"set_string_var": "pf_mom_<global_val:pf_fl_k>", "target_var": ctx("mr"), "parse_tags": True},
    {"copy_var": {"var_val": "mr"}, "target_var": g("pf_find_uid")},
    {"if": {"compare_string": [g("pf_find_uid"), "AVATAR"]}, "then": [{"run_eocs": {"id": "PF_FL_due_av", "effect": [m("u_pf_preg_t = time('now') - time('1 d') * %s * pf_fl_frac" % TERM_DAYS)]}, "alpha_talker": "avatar"}],
     "else": [{"run_eocs": "PF_FIND_by_uid", "alpha_talker": "avatar"},
              {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": {"id": "PF_FL_due_np", "effect": [m("u_pf_preg_t = time('now') - time('1 d') * %s * pf_fl_frac" % TERM_DAYS)]}, "alpha_talker": g("pf_find_who")}],
               "else": [{"u_run_npc_eocs": ["PF_FL_due_np"], "unique_ids": [g("pf_find_uid")], "local": False}]}]},
    m("pf_fl_k += 1")]))
FL.append(("PF_FL_mid", "Pregnancy: everyone expecting is halfway along", "Moves every pregnancy to the middle stage, then runs the step (cravings, and your partner carrying the load, start here).",
           [m("pf_fl_frac = 0.5"), m("pf_fl_k = 0"), {"run_eocs": "PF_FL_due_k", "condition": m("pf_fl_k < min(value_or(pf_moms_n, 0), 12)"), "iterations": 13}, {"run_eocs": "PF_FAM_preg_tick"}]))
FL.append(("PF_FL_babies", "Babies: run the care step now", "Every baby nearby gets looked after.", [{"run_eocs": "PF_FAM_baby_tick"}]))
FL.append(("PF_FL_age2", "Growth: every child born here ages two years", "Moves every listed child's birth back two years (at the current pace) and runs the growth step.",
           [m("pf_fl_years = 2"), m("pf_fl_k = 0"), {"run_eocs": "PF_FL_age_k", "condition": m("pf_fl_k < min(value_or(pf_kids_n, 0), 30)"), "iterations": 31}, {"run_eocs": "PF_FAM_grow_tick"}]))
FL.append(("PF_FL_age16", "Growth: every child born here ages sixteen years", "As above, sixteen years: children who reach 18 grow up.",
           [m("pf_fl_years = 16"), m("pf_fl_k = 0"), {"run_eocs": "PF_FL_age_k", "condition": m("pf_fl_k < min(value_or(pf_kids_n, 0), 30)"), "iterations": 31}, {"run_eocs": "PF_FAM_grow_tick"}]))
FL.append(("PF_FL_age_k", None, None, [
    {"set_string_var": "pf_kid_<global_val:pf_fl_k>", "target_var": ctx("kr"), "parse_tags": True},
    {"u_run_npc_eocs": [{"id": "PF_FL_age_one", "effect": [m("u_pf_born_t = u_pf_born_t - time('1 d') * 364 * pf_fl_years / %s" % PACE)]}], "unique_ids": [{"var_val": "kr"}], "local": False},
    m("pf_fl_k += 1")]))
FL.append(("PF_FL_orphan", "Orphans: children nearby look for a home now", "Runs the orphan check: any orphaned child in the bubble is taken in by the adult who cares most (if anyone does).",
           [{"run_eocs": "PF_FAM_orphan_tick"}]))
FL.append(("PF_FL_kids", "Kids: run a kids' day step now (play, chores, questions, grief)", "Runs the 2-hourly kids' step immediately (it still needs calm).",
           [{"run_eocs": {"id": "PF_FL_kids_now", "effect": [{"run_eocs": "PF_THREAT_scan"}, {"if": m("pf_threat == 0"), "then": [
               m("pf_kl = 0"), m("pf_kid_force = 1"), {"u_location_variable": g("pf_fm_avpos")}, {"u_run_npc_eocs": ["PF_FAM_kid_moment"], "local": True, "npc_range": 40}, m("pf_kid_force = 0")],
               "else": [say("[family lab] Not calm: something hostile is near.")]}]}}]))
FL.append(("PF_FL_carry", "Babies: run the carry and help step now", "Carried babies catch up with their carrier; an expecting you gets your partner's help if they're close.",
           [{"run_eocs": "PF_FAM_follow_tick"}]))
FL.append(("PF_FL_bandpreg", "Off-screen: 10 band evenings, every band couple conceives", "Runs 10 off-screen camp evenings for every band with the conception chance at 100%, then puts it back.  Partners camping together conceive; their pregnancies move along by unique id, and births wait until the mother is near you.",
           [m("pf_fl_saved = value_or(pf_set_preg_chance, 8)"), m("pf_set_preg_chance = 100"),
            m("pf_fl_bc0 = value_or(pf_band_conceptions_total, 0)"),
            m("pf_fl_prom = 0"), m("pf_fl_vis = 0"), m("pf_fl_sw = 0"), m("pf_fl_p2 = 0"), m("pf_fl_fem = 0"), m("pf_fl_mo = 0"), m("pf_fl_pr = 0"), m("pf_fl_av = 0"), m("pf_fl_man = 0"), m("pf_fl_same = 0"), m("pf_fl_setp = value_or(pf_set_preg, 1)"), m("pf_band_i = 0"), {"run_eocs": "PF_FL_bp_band_i", "condition": m("pf_band_i < pf_band_n"), "iterations": 1000},
            say("[family lab] Bands: <global_val:pf_band_n>, people reached <global_val:pf_fl_vis>, in a couple <global_val:pf_fl_sw> (women <global_val:pf_fl_fem>: mourning <global_val:pf_fl_mo>, expecting <global_val:pf_fl_pr>, with you <global_val:pf_fl_av>, with a man <global_val:pf_fl_man>, partner in the same band <global_val:pf_fl_same>; pregnancy setting <global_val:pf_fl_setp>; already partners <global_val:pf_fl_p2>), made partners now <global_val:pf_fl_prom>."),
            {"run_eocs": "PF_LL_bandeve"},
            m("pf_set_preg_chance = pf_fl_saved"),
            m("pf_fl_bc = value_or(pf_band_conceptions_total, 0) - pf_fl_bc0"),
            m("pf_fl_calls = value_or(pf_bc_calls, 0)"),
            say("[family lab] Band conceptions this run: <global_val:pf_fl_bc> (couples camping together, all time: <global_val:pf_fl_calls>).")]))
FL.append(("PF_FL_bp_band_i", None, None, [
    {"set_string_var": "pf_slot_<global_val:pf_band_i>", "target_var": ctx("ref"), "parse_tags": True},
    {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}},
     "then": [{"u_run_npc_eocs": ["PF_FL_bp_band"], "unique_ids": [{"var_val": "ref"}], "local": False}]},
    m("pf_band_i += 1")]))
FL.append(("PF_FL_bp_band", None, None, [{"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_fl_m5")}] +
    [{"copy_var": {"u_val": "pf_member_%d" % k}, "target_var": g("pf_fl_m%d" % k)} for k in range(5)] + [{"run_eocs": "PF_FL_bp_promote"}] + [
    {"if": {"not": {"compare_string": [{"u_val": "pf_member_%d" % k}, "none"]}},
     "then": [{"u_run_npc_eocs": ["PF_FL_bp_promote"], "unique_ids": [{"u_val": "pf_member_%d" % k}], "local": False}]} for k in range(5)]))
FL.append(("PF_FL_bp_promote", None, None, [
    m("pf_fl_vis += 1"),
    {"if": m("value_or(u_pf_has_sweet, 0) == 1"), "then": [m("pf_fl_sw += 1"), {"if": m("value_or(u_pf_rel_stage, 0) >= 2"), "then": [m("pf_fl_p2 += 1")]},
        {"if": m("u_gender() == 0"), "then": [m("pf_fl_fem += 1"),
            {"if": m("time('now') < value_or(u_pf_mourn_until, 0)"), "then": [m("pf_fl_mo += 1")]},
            {"if": m("value_or(u_pf_preg, 0) == 1"), "then": [m("pf_fl_pr += 1")]},
            {"if": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}, "then": [m("pf_fl_av += 1")]},
            {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_fm_dad")},
            {"set_string_var": "pf_reg_<global_val:pf_fm_dad>_g", "target_var": ctx("dg"), "parse_tags": True},
            {"if": m("value_or(v_dg, -1) == 1"), "then": [m("pf_fl_man += 1")]},
            {"if": {"or": [{"compare_string": [{"u_val": "pf_sweet"}, g("pf_fl_m%d" % k)]} for k in range(6)]}, "then": [m("pf_fl_same += 1")]}]}]},
    {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), m("value_or(u_pf_rel_stage, 1) <= 1")]},
     "then": [m("u_pf_rel_stage = 2"), m("u_pf_stage_since = time('now') - time('21 d')"), m("pf_fl_prom += 1")]}]))
FL.append(("PF_FL_teach", "Kids: the nearest adult teaches the nearest child now", "Forces a lesson between the nearest child and an adult nearby (you, if you're closer than 8 tiles).",
           [m("pf_kl = 0"), m("pf_kid_force = 1"), {"u_location_variable": g("pf_fm_avpos")},
            {"u_run_npc_eocs": [{"id": "PF_FL_teach_one", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}, m("pf_kl == 0")]},
                                 "effect": [{"run_eocs": "PF_ID_ensure"}, {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_kid_uid")},
                                            {"u_location_variable": {"u_val": "pf_pos"}}, m("pf_kid_avnear = distance(u_pf_pos, pf_fm_avpos) <= 8"),
                                            m("u_pf_taught_t = -1"), {"run_eocs": "PF_FAM_kid_learn"}]}], "local": True, "npc_range": 30},
            m("pf_kid_force = 0"),
            {"if": m("pf_kl == 0"), "then": [say("[family lab] No child nearby, or nobody knows more than they do.")]}]))
FL.append(("PF_FL_stats", "Stats: family", "Conceptions (and how many at a band camp), births, children listed, adoptions, grown up.",
           [m("pf_fs_a = value_or(pf_conceptions_total, 0)"), m("pf_fs_b = value_or(pf_births_total, 0)"), m("pf_fs_c = value_or(pf_kids_n, 0)"),
            m("pf_fs_d = value_or(pf_adoptions_total, 0)"), m("pf_fs_e = value_or(pf_grownup_total, 0)"),
            m("pf_fs_f = value_or(pf_band_conceptions_total, 0)"), m("pf_fs_g = value_or(pf_taught_total, 0)"),
            say("[family] conceptions <global_val:pf_fs_a> (at band camps <global_val:pf_fs_f>), births <global_val:pf_fs_b>, children listed <global_val:pf_fs_c>, adoptions <global_val:pf_fs_d>, grown up <global_val:pf_fs_e>, lessons <global_val:pf_fs_g>.")]))
FMENU = [x for x in FL if x[1]]
lab = [eoc("PF_FL_open", [{
    "run_eoc_selector": [i for i, _, _, _ in FMENU], "names": [n for _, n, _, _ in FMENU], "descriptions": [d for _, _, d, _ in FMENU],
    "keys": [c for c in "abcdefghijklmnopqrstuvwxyz"][:len(FMENU)], "title": "Family lab (v0.3)", "allow_cancel": True}])]
lab += [eoc(i, eff) for i, _, _, eff in FL]
files["lab_family.json"] = lab

os.makedirs(OUT, exist_ok=True)
for fname, data in files.items():
    json.dump(data, open(os.path.join(OUT, fname), "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
print("family written:", {k: len(v) for k, v in files.items()})
