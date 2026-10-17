"""Generates mods/PeopleFirst/home/*.json and mod_interactions/*: v0.4 "Homestead" (concept §5.2, §5.5, §7 phase 2, §8).

Usage: python tools/gen_home.py mods/PeopleFirst

- Home: you name a place home (main menu: Home).  Evenings there happen around a table or a couch when no fire burns
  (life/fire.json calls PF_HOME_hearth), with props (cards, books, a piano) and instruments (guitar, violin) feeding
  the parallel play, a "Home" morale, and breakfast when you wake up there.
- Residents: people who live with you.  Ask anyone (a whole A-Life band comes along: it leaves the roster) on the
  People menu.  Residents drift back home during the day.
- The world: natural A-Life population.  Every 3 hours, below the population cap (Settings), a band may appear at the
  edge of the bubble: hunters (3 adults), a family on the move (a couple and 1-2 kids), or a family settled in a house.
- Mod interactions (soft): Mind Over Matter telepaths feel a loved one's fear; Xedra Evolved companions find out
  what you are (vampire) and either keep your secret or are frightened of you.
"""
import json, string, os, sys

ROOT = sys.argv[1]
def m(e): return {"math": [e]}
def g(n): return {"global_val": n}
def ctx(n): return {"context_val": n}
def eoc(id_, effect, comment=None, condition=None, **extra):
    o = {"type": "effect_on_condition", "id": id_}
    if comment: o["//"] = comment
    if condition: o["condition"] = condition
    o.update(extra)
    o["effect"] = effect
    return o
def say(text, t="info"): return {"u_message": text, "type": t}
def name_into(gvar, tag="<u_name>"): return {"set_string_var": tag, "target_var": g(gvar), "parse_tags": True}
def cooldown_ok_c(var, dur):
    return {"or": [m(f"time_since({var}) < 0"), m(f"time_since({var}) > time('{dur}')")]}
def line(key): return {"run_eocs": "PF_SAY_home", "alpha_talker": "avatar", "variables": {"line": key}}
def by_uid(eocs, uid): return {"u_run_npc_eocs": eocs, "unique_ids": [uid], "local": False}
CALM_LINES = "value_or(pf_set_chatter, 1) == 1"
HORN_OFF = [{"if": m("value_or(pf_horn_on, 1) == 1"), "then": [m("pf_horn_on = 0"),
               {"run_eocs": "PF_HML_horn_back", "time_in_future": "10 minutes"}]},
            m("pf_horn_active = 0"), {"u_message": "[home lab] The Horn is off for 10 minutes.", "type": "info"}]
ADULT = {"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18")]}
AT_HOME = "value_or(pf_home_set, 0) == 1"
# v0.5 Town pass 3: a family that joined the town lives in its own house (u_pf_house); everyone else's anchor is home
ANCHOR = [{"copy_var": g("pf_home_loc"), "target_var": {"u_val": "pf_anchor"}},
          {"if": m("has_var(u_pf_house)"), "then": [{"copy_var": {"u_val": "pf_house"}, "target_var": {"u_val": "pf_anchor"}}]}]
NIGHT_KEY = "floor((time('now') - time('12 h')) / time('1 d'))"
ON_WATCH = {"and": [m("value_or(u_pf_on_watch, 0) == 1"), m(f"value_or(u_pf_watch_night, -1) == {NIGHT_KEY}")]}
WATCH_RECENT = m("value_or(pf_wt_seen_t, -1) >= time('now') - time('3 m')")
TODAY = "floor(time('now') / time('1 d'))"
PACE = "(value_or(pf_set_grow, 1) == 0 ? 1 : (value_or(pf_set_grow, 1) == 1 ? 12 : 120))"

files = {}

# ============================================================ DEFINITIONS
files["defs.json"] = [
    {"type": "morale_type", "id": "PF_morale_home", "text": "An evening at home"},
    {"type": "morale_type", "id": "PF_morale_breakfast", "text": "Breakfast at home"},
    {"type": "npc", "id": "PF_WANDERER", "//": "A natural A-Life person (v0.4).  Mission 2 (shelter) turns off vanilla goal-seeking; A-Life and People First move them.",
     "name_suffix": "wanderer", "class": "NC_HUNTER", "attitude": 0, "mission": 2, "chat": "TALK_PF_PERSON", "faction": "no_faction"},
    {"type": "npc", "id": "PF_SETTLER", "//": "A natural A-Life person in a family (v0.4).",
     "class": "NC_SCAVENGER", "attitude": 0, "mission": 2, "chat": "TALK_PF_PERSON", "faction": "no_faction"},
    # lab test of the open threads: both parents of two spawned families were women (random genders), so "mom" and "dad" were labels only
    {"type": "npc", "id": "PF_SETTLER_F", "//": "A family's mother (v0.7): PF_SETTLER, female.", "gender": "female",
     "class": "NC_SCAVENGER", "attitude": 0, "mission": 2, "chat": "TALK_PF_PERSON", "faction": "no_faction"},
    {"type": "npc", "id": "PF_SETTLER_M", "//": "A family's other parent, usually (v0.7): PF_SETTLER, male.", "gender": "male",
     "class": "NC_SCAVENGER", "attitude": 0, "mission": 2, "chat": "TALK_PF_PERSON", "faction": "no_faction"},
    {"type": "npc", "id": "PF_KID", "//": "A natural A-Life child (v0.4).  Tiny (SMALL2) and PF_CHILD (CANNOT_ATTACK) are added at spawn.  name_suffix: without one, the game shows a random profession after the name (v0.7: a child titled 'Convict').",
     "name_suffix": "child", "class": "NC_NONE", "attitude": 0, "mission": 2, "chat": "TALK_PF_PERSON", "faction": "no_faction"},
    {"type": "talk_topic", "id": "TALK_PF_PERSON",
     "//": "v0.7 (concept 15.3): the line reads their state: a child's family (who they lost, who looks after them now), grief, a new roof, a partner, the road.",
     "dynamic_line": {'npc_has_trait': 'PF_CHILD', 'yes': {'math': ['value_or(n_pf_orphaned, 0) == 1'], 'yes': "*hugs their knees and won't look up*  Everyone's gone.  I stayed where they told me.  I stayed right here.", 'no': {'math': ["has_var(n_pf_lost_t) * (time('now') < value_or(n_pf_mourn_until, 0))"], 'yes': {'math': ['value_or(n_pf_guard_you, 0) == 1'], 'yes': "<npc_val:pf_lost_name> is gone.  *holds on to your sleeve*  You're staying, right?", 'no': {'math': ['has_var(n_pf_guard_name)'], 'yes': '<npc_val:pf_lost_name> is gone.  <npc_val:pf_guard_name> looks after me now.', 'no': '<npc_val:pf_lost_name> is gone.  Nobody will tell me where.'}}, 'no': {'math': ['has_var(n_pf_lost_t) * (value_or(n_pf_lost_healed, 0) == 1)'], 'yes': "I still miss <npc_val:pf_lost_name>.  But it's okay.  Mostly.", 'no': {'math': ['value_or(n_pf_resident, 0) == 1'], 'yes': 'Are we staying here forever?  I like it here.', 'no': 'My family says not to talk to strangers.  Are you a stranger?'}}}}, 'no': {'math': ["time('now') < value_or(n_pf_mourn_until, 0)"], 'yes': "*doesn't quite meet your eyes*  Sorry.  It's been a hard few days.", 'no': {'math': ['value_or(n_pf_envoy, 0) == 1'], 'yes': "I'm only here with a message.  Nothing personal.", 'no': {'math': ['value_or(n_pf_resident, 0) == 1'], 'yes': {'math': ["time('now') - value_or(n_pf_resident_since, 0) < time('3 d')"], 'yes': 'Still getting used to a roof.  I keep waking up and listening for the dead.', 'no': {'math': ['value_or(n_pf_has_sweet, 0) == 1'], 'yes': "It's good here.  We're good here.", 'no': "It's good to sleep under a roof again.  Thank you."}}, 'no': {'math': ['value_or(n_pf_settled, 0) == 1'], 'yes': "This is our place.  We don't want trouble.", 'no': {'math': ["time('now') - value_or(n_pf_hurt_t, -999999999) < time('3 d')"], 'yes': "*favors one side*  Ran into the dead on the road.  I'll live.", 'no': "We keep moving.  It's safer that way."}}}}}},
     "responses": [{"text": "Take care of yourself.", "topic": "TALK_DONE"}]},
]

# ============================================================ HOME (menu)
files["home.json"] = [
    eoc("PF_HOME_open", [
        {"if": m(AT_HOME), "then": [
            {"u_location_variable": g("pf_hm_av")},
            m("pf_hm_dist = round(distance(pf_hm_av, pf_home_loc))"),
            m("pf_hm_res = value_or(pf_residents_n, 0)"),
            {"if": m("pf_hm_res == 1"), "then": [{"set_string_var": "1 person has", "target_var": g("pf_hm_restxt")}],
             "else": [{"set_string_var": "<global_val:pf_hm_res> people have", "target_var": g("pf_hm_restxt"), "parse_tags": True}]}]},
        {"run_eoc_selector": ["PF_HOME_set", "PF_HOME_move", "PF_HOME_forget", "PF_HOME_status", "PF_HOME_roster_menu", "PF_HOME_rumors",
                              "PF_TOWN_status", "PF_TOWN_name", "PF_TOWN_field_here", "PF_TOWN_ask_animals", "PF_TWATCH_menu", "PF_KEEP_menu", "PF_KEEP_call_now", "PF_KEEP_laws_menu", "PF_KEEP_propose_menu", "PF_KEEP_wall_start", "PF_NB_menu", "PF_HOUSE_stores_here", "PF_HOUSE_corner_here", "PF_HOUSE_pack_sack"],
         "names": ["Make this place our home", "Make this place our home instead", "This isn't home anymore", "Where is home?", "Who does what", "What people have heard",
                   "How the place is doing", "Name this place", "Plant a field here", "Ask the neighbors for animals", "Tonight's watch", "Who's in charge", "Call a meeting", "The laws of the place", "Put a law to the meeting", "Build a wall around the place", "The neighbors", "Keep the stores here", "This is my corner", "Pack a sack of supplies"],
         "descriptions": ["Evenings here gather around the table or the couch when there's no fire, people who live with you come back here, and waking up here feels like waking up at home.",
                          "Home moves here.  The people who live with you will come here from now on.",
                          "Forget the home.  The people who live with you stay where they are.",
                          "How far home is, and how many people live there.",
                          "The jobs of the people who live with you (those nearby).  Change one on their People screen.",
                          "Rumors about other people out there, as they came up at the fire.",
                          "The animals, the field, and how many people live here.",
                          "Give your home a name.  The people who live here will use it.",
                          "Mark a 5x5 plot around you as the field.  It's planted in spring or summer and harvested about a month later (by the farmer, if someone has that job).",
                          "Put the word out that you could use some animals (once a week).  Neighbors bring hens, a goat or even a cow the next morning you're home.",
                          "Who has the watch tonight.  Once at least three grown-ups live here, a watch goes up at ten every night: two shifts, posts at the edge of the place, and whoever sees something first raises the alarm.",
                          "Who leads the place, and when the next meeting is.  Once at least four grown-ups besides you live here, they meet one evening a week: they choose a chief, and bring their quarrels for the chief to settle.",
                          "You're chief: call everyone to a meeting tomorrow evening.",
                          "The laws the meeting has made, and what's up at the next one.",
                          "Propose a law (or doing away with one) at the next meeting.  Everyone votes; you do too.",
                          "A palisade all the way round, 12 tiles out from home, a gate in each side: one side a day, from tomorrow morning, while you're home.  The gates are shut at night.",
                          "The settlements out there that know of the place: who leads them, how things stand, and what's agreed.",
                          "The household's food, water and supplies are kept where you stand (and anything stray gets carried over).  Every meal, delivery and harvest goes here from now on.",
                          "Where you stand is yours: the people who live here won't tidy anything within a step of it.  Keep your own food and gear here.",
                          "Six things to eat from the stores, tied up in a sack to carry.  Give it to a band out on the road (People: Bring their people supplies)."],
         "keys": ["h", "m", "f", "w", "j", "r", "s", "n", "p", "a", "t", "c", "g", "v", "o", "b", "e", "k", "y", "x"], "title": "Home", "hide_failing": True, "allow_cancel": True},
    ], "u = avatar.  Home screen (main menu: Home)."),
    eoc("PF_HOME_set", [{"u_location_variable": g("pf_home_loc")}, m("pf_home_set = 1"), {"run_eocs": "PF_STORES_ensure"}, m("pf_home_since = time('now')"), line("home_set")],
        condition=m("value_or(pf_home_set, 0) == 0")),
    eoc("PF_HOME_move", [{"u_location_variable": g("pf_home_loc")}, {"run_eocs": "PF_STORES_ensure"}, m("pf_home_since = time('now')"), line("home_move")],
        condition={"and": [m(AT_HOME), m("pf_hm_dist > 30")]}),
    eoc("PF_HOME_forget", [m("pf_home_set = 0"), line("home_forget")], condition=m(AT_HOME)),
    eoc("PF_HOME_roster_menu", [{"run_eocs": "PF_HOME_roster"}], condition=m(AT_HOME)),
    eoc("PF_HOME_status", [
        {"if": m("pf_hm_dist <= 30"), "then": [line("home_here")], "else": [line("home_far")]},
        # v0.8: and where the stores are (an automatic choice was invisible: food in a locker, out of the V list)
        {"if": m("has_var(pf_stores_loc)"), "then": [m("pf_hm_sdist = round(distance(pf_hm_av, pf_stores_loc))"),
            # Kinfold day 136: "2 steps from you" and three wrong guesses; say which way
            {"copy_var": g("pf_hm_av"), "target_var": g("pf_sd_n")}, {"location_variable_adjust": g("pf_sd_n"), "x_adjust": 0, "y_adjust": -1},
            {"copy_var": g("pf_hm_av"), "target_var": g("pf_sd_s")}, {"location_variable_adjust": g("pf_sd_s"), "x_adjust": 0, "y_adjust": 1},
            {"copy_var": g("pf_hm_av"), "target_var": g("pf_sd_e")}, {"location_variable_adjust": g("pf_sd_e"), "x_adjust": 1, "y_adjust": 0},
            {"copy_var": g("pf_hm_av"), "target_var": g("pf_sd_w")}, {"location_variable_adjust": g("pf_sd_w"), "x_adjust": -1, "y_adjust": 0},
            {"set_string_var": "", "target_var": g("pf_hm_sns")}, {"set_string_var": "", "target_var": g("pf_hm_sew")},
            {"if": m("distance(pf_sd_n, pf_stores_loc) < distance(pf_sd_s, pf_stores_loc)"), "then": [{"set_string_var": "north", "target_var": g("pf_hm_sns")}]},
            {"if": m("distance(pf_sd_s, pf_stores_loc) < distance(pf_sd_n, pf_stores_loc)"), "then": [{"set_string_var": "south", "target_var": g("pf_hm_sns")}]},
            {"if": m("distance(pf_sd_e, pf_stores_loc) < distance(pf_sd_w, pf_stores_loc)"), "then": [{"set_string_var": "east", "target_var": g("pf_hm_sew")}]},
            {"if": m("distance(pf_sd_w, pf_stores_loc) < distance(pf_sd_e, pf_stores_loc)"), "then": [{"set_string_var": "west", "target_var": g("pf_hm_sew")}]},
            {"set_string_var": "<global_val:pf_hm_sns><global_val:pf_hm_sew>", "target_var": g("pf_hm_sdir"), "parse_tags": True},
            {"if": m("pf_hm_sdist <= 1"), "then": [line("stores_at_hand")], "else": [line("stores_dist")]}]},
    ], condition=m(AT_HOME)),
]

# ============================================================ EVENINGS AT HOME (called from life/fire.json)
def find_furn(furn, then_eocs, else_eocs, rmax=12):
    return {"u_location_variable": g("pf_fire_loc"), "furniture": furn, "target_max_radius": rmax,
            "true_eocs": then_eocs, "false_eocs": else_eocs}
HEARTH_GO = [{"id": "PF_HOME_hearth_go", "effect": [m("pf_eve_home = 1"), {"run_eocs": "PF_FIRE_step"}]}]
files["evening.json"] = [
    eoc("PF_HOME_hearth", [
        {"u_location_variable": g("pf_hm_av")},
        {"if": m("distance(pf_hm_av, pf_home_loc) <= 30"), "then": [
            find_furn("f_table", HEARTH_GO, [{"id": "PF_HOME_try_sofa", "effect": [
                find_furn("f_sofa", ["PF_HOME_hearth_go"], [{"id": "PF_HOME_try_chair", "effect": [
                    find_furn("f_armchair", ["PF_HOME_hearth_go"], [{"id": "PF_HOME_try_bench", "effect": [
                        find_furn("f_bench", ["PF_HOME_hearth_go"], [{"id": "PF_HOME_try_bench_w", "effect": [
                            find_furn("f_bench_wooden", ["PF_HOME_hearth_go"], [])]}])]}])]}])]}])]},
    ], "u = avatar, during the evening, when no fire burns within 15 tiles.  At home (within 30 tiles of it), the evening gathers around the nearest table, else couch, else armchair, else bench (playtest 3: an evac shelter has only benches), within 12 tiles: the same evening as at a fire (seats, beats, romance, grief), with lines for indoors (pf_eve_home = 1).",
        condition=m(AT_HOME)),
    eoc("PF_HOME_prop_act", [
        m("pf_pa = value_or(pf_prop_force, 0) == 1 ? rand(2) : rand(5)"),
        {"if": {"and": [m("pf_pa <= 1"), {"u_has_items": {"item": "acoustic_guitar", "count": 1}}]},
         "then": [{"set_string_var": "act_guitar", "target_var": g("pf_act")}, m("pf_pa = 9")]},
        {"if": {"and": [m("pf_pa <= 1"), {"u_has_items": {"item": "violin", "count": 1}}]},
         "then": [{"set_string_var": "act_violin", "target_var": g("pf_act")}, m("pf_pa = 9")]},
        {"if": {"and": [m("value_or(pf_eve_home, 0) == 1"), m("pf_pa < 9")]}, "then": [
            {"if": m("pf_pa == 0"), "then": [{"u_location_variable": g("pf_pa_at"), "furniture": "f_bookcase", "target_max_radius": 12,
                                              "true_eocs": [{"id": "PF_HOME_pa_read", "effect": [{"set_string_var": "act_read", "target_var": g("pf_act")}]}]}]},
            {"if": m("pf_pa == 1"), "then": [{"u_location_variable": g("pf_pa_at"), "furniture": "f_piano", "target_max_radius": 12,
                                              "true_eocs": [{"id": "PF_HOME_pa_piano", "effect": [{"set_string_var": "act_piano", "target_var": g("pf_act")}]}]}]},
            {"if": m("pf_pa == 2"), "then": [{"u_location_variable": g("pf_pa_at"), "furniture": "f_table", "target_max_radius": 6,
                                              "true_eocs": [{"id": "PF_HOME_pa_cards", "effect": [{"set_string_var": "act_cards", "target_var": g("pf_act")}]}]}]},
            {"if": {"and": [m("pf_pa == 3"), m("rand(2) == 0")]}, "then": [{"u_location_variable": g("pf_pa_at"), "furniture": "f_sofa", "target_max_radius": 6,
                                              "true_eocs": [{"id": "PF_HOME_pa_couch", "effect": [{"set_string_var": "act_couch", "target_var": g("pf_act")}]}]}]}]},
    ], "u = someone at tonight's evening, after their temperament picked an activity (life/fire.json PF_FIRE_activity_do).  Only quiet, storytelling and whittling evenings are open to change.  Anyone carrying a guitar or violin may play (at a fire too); at home, a bookcase means someone reads aloud, a piano gets played, the table gets a card game, and the couch gets a nap.",
        condition={"or": [{"compare_string": [g("pf_act"), "act_quiet", "act_story", "act_whittle"]}, m("value_or(pf_prop_force, 0) == 1")]}),
    eoc("PF_HOME_beat_extra", [
        {"u_location_variable": g("pf_hm_av")},
        {"if": m("distance(pf_hm_av, pf_fire_loc) <= 10"), "then": [
            {"u_add_morale": "PF_morale_home", "bonus": 8, "max_bonus": 8, "duration": "8 hours", "decay_start": "4 hours"},
            m("pf_home_evenings_total = value_or(pf_home_evenings_total, 0) + 1")]},
        {"u_run_npc_eocs": ["PF_FIRE_unseat"], "local": True, "npc_range": 40},
    ], "u = avatar, after an evening at home.  If you were there: 'An evening at home' (+8).  Then everyone gets up again: seats packed between furniture had people shoving past each other all night (vanilla 'excuse me' barks), so indoors the seats are let go once the evening has happened."),
    eoc("PF_HOME_wake", [
        {"u_location_variable": g("pf_hm_av")},
        {"if": m("distance(pf_hm_av, pf_home_loc) <= 30"), "then": [
            m("pf_bk_day = %s" % TODAY),
            m("pf_hm_best = -1"),
            {"u_run_npc_eocs": ["PF_HOME_cook_cand"], "local": True, "npc_range": 20},
            {"if": m("pf_hm_best >= 0"), "then": [{"run_eocs": "PF_HOME_cook", "alpha_talker": g("pf_hm_cook"), "beta_talker": "avatar"}]}]},
    ], "Signal: you wake up at home.  Whoever there cares most about you (warmth 20+, mother hens first) has made breakfast.  Once a day.",
        condition={"and": ["u_is_avatar", m(AT_HOME), m("value_or(pf_bk_day, -1) != %s" % TODAY), m("time_since('midnight', 'unit': 'hours') >= 4"),
                           m("time_since('midnight', 'unit': 'hours') < 13")]},
        eoc_type="EVENT", required_event="character_wakes_up"),
    eoc("PF_HOME_breakfast_late_check", [
        m("pf_bk_awake = 1"),
        {"u_location_variable": g("pf_hm_av")},
        {"if": m("distance(pf_hm_av, pf_home_loc) <= 30"), "then": [
            m("pf_bk_day = %s" % TODAY),
            m("pf_hm_best = -1"),
            {"u_run_npc_eocs": ["PF_HOME_cook_cand"], "local": True, "npc_range": 20},
            {"if": m("pf_hm_best >= 0"), "then": [{"run_eocs": "PF_HOME_cook", "alpha_talker": g("pf_hm_cook"), "beta_talker": "avatar"}]}]},
        m("pf_bk_awake = 0"),
    ], "Every 30 minutes, 07:00-11:00: if you're home and awake and nobody has made breakfast yet (full run: a night alarm woke you, which isn't a 'wakes up' event, so the morning had no breakfast), the cook makes it now.",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), {"not": {"u_has_effect": "sleep"}}, m("value_or(pf_bk_day, -1) != %s" % TODAY),
                           m("time_since('midnight', 'unit': 'hours') >= 7"), m("time_since('midnight', 'unit': 'hours') < 11")]}),
    eoc("PF_HOME_cook_cand", [
        {"run_eocs": "PF_ID_ensure"},
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        m("_s = pf_read_w"),
        {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("_s += 25")]},
        {"if": m("value_or(u_pf_role, 0) == 1"), "then": [m("_s += 30")]},
        {"if": {"and": [m("_s >= 20"), m("_s > pf_hm_best")]}, "then": [m("pf_hm_best = _s"), {"u_set_talker": g("pf_hm_cook")}]},
    ], condition=ADULT),
    eoc("PF_HOME_cook", [
        {"run_eocs": "PF_STORES_ensure"},
        name_into("pf_say_a"),
        m("_r = rand(2)"),
        # full run day 161: 11 pancakes at the stores (3 a morning, and only you eat).  With 6 or more breakfast leftovers
        # waiting, the cook warms those up instead of making more.
        m("pf_bk_left = 0"),
        {"u_map_run_item_eocs": "all", "loc": g("pf_home_loc"), "min_radius": 0, "max_radius": 20,
         "search_data": [{"id": ["pancakes", "scrambled_eggs"]}],
         "true_eocs": [{"id": "PF_HOME_bk_count", "effect": [m("pf_bk_left += 1")]}]},
        {"if": m("pf_bk_left >= 6"), "then": [m("_r = 9"), {"set_string_var": "yesterday's leftovers, warmed up", "target_var": g("pf_say_b")}]},
        # full run: "a pot of oatmeal" / "a stack of pancakes" were one 90-120 kcal serving; the amount now matches the words
        {"if": m("_r == 0"), "then": [{"map_spawn_item": "oatmeal", "loc": g("pf_stores_loc"), "count": 3}, {"set_string_var": "a pot of oatmeal", "target_var": g("pf_say_b")}]},
        {"if": m("_r == 1"), "then": [{"map_spawn_item": "pancakes", "loc": g("pf_stores_loc"), "count": 3}, {"set_string_var": "a stack of pancakes", "target_var": g("pf_say_b")}]},
        {"if": m("_r == 2"), "then": [{"map_spawn_item": "scrambled_eggs", "loc": g("pf_stores_loc"), "count": 2}, {"set_string_var": "a pan of eggs", "target_var": g("pf_say_b")}]},
        # v0.8: breakfast with the stores, the coffee into your hands.  Day 150: about 40 full mugs at the stores (a mug every
        # morning, mostly not drunk, tidied back); no new coffee while 4 wait there.  Day 158: 37 full mugs in Dante's own
        # corner (handed to him as he woke there; the tidy pass never touches a corner), unseen by a count at the stores.
        # Count full mugs anywhere around home.
        m("pf_cf_n = 0"),
        {"u_map_run_item_eocs": "all", "loc": g("pf_home_loc"), "min_radius": 0, "max_radius": 20,
         "search_data": [{"id": "ceramic_mug", "condition": m("n_weight() >= 348000")}],
         "true_eocs": [{"id": "PF_HOME_cf_count", "effect": [m("pf_cf_n += 1")]}]},
        {"if": m("pf_cf_n < 4"), "then": [{"run_eocs": "PF_GIVE_coffee", "alpha_talker": "avatar"}]},
        m("_b = rand(2)"), {"if": m("_b == value_or(pf_bk_last, -1)"), "then": [m("_b = (_b + 1) % 3")]}, m("pf_bk_last = _b"),
        # playtest 3: a cold night, you slept till 11 and the cook had given up on you; a late riser gets it kept warm
        # day 151-152: "You were up before any of us.  Sit, eat." twice, both times right after Dante walked in from the road
        {"if": m("(value_or(pf_bk_awake, 0) == 1) * (time('now') - value_or(pf_aw_back_t, -999999) < time('3 h'))"),
         "then": [m("pf_bk_awake = 0"), line("breakfast_back")],
         "else": [{"if": m("value_or(pf_bk_awake, 0) == 1"), "then": [m("pf_bk_awake = 0"), line("breakfast_awake")],
         "else": [{"if": m("time_since('midnight', 'unit': 'hours') >= 10"), "then": [line("breakfast_late")], "else": [
            {"if": m("_b == 0"), "then": [line("breakfast")]},
            {"if": m("_b == 1"), "then": [line("breakfast_1")]},
            {"if": m("_b == 2"), "then": [line("breakfast_2")]}]}]}]},
        {"run_eocs": {"id": "PF_HOME_bk_morale", "effect": [{"u_add_morale": "PF_morale_breakfast", "bonus": 6, "max_bonus": 6, "duration": "4 hours", "decay_start": "2 hours"}]}, "alpha_talker": "avatar"},
        m("pf_m_str_in = 40"), {"run_eocs": "PF_MK_care_given"},
    ], "Alpha = the cook, beta = you.  Breakfast and coffee at your feet, a care moment, and 'Breakfast at home' (+6)."),
]

def chore_line(role, key, n):
    """Effects: the job's line (one of n versions, never the same twice running), once per round per job."""
    return [{"if": m(f"pf_ch_say * (pf_ch_said_{role} == 0)"), "then": [
        m("pf_ch_l += 1"), m(f"pf_ch_said_{role} = 1"),
        m(f"_v = rand({n - 1})"), {"if": m(f"_v == value_or(pf_chl_{key}, -1)"), "then": [m(f"_v = (_v + 1) % {n}")]}, m(f"pf_chl_{key} = _v")] +
        [{"if": m(f"_v == {i}"), "then": [line(key if i == 0 else f"{key}_{i}")]} for i in range(n)]}]
# ============================================================ RESIDENTS (recruitable people and families)
files["residents.json"] = [
    eoc("PF_HOME_invite", [
        {"run_eocs": "PF_ID_ensure", "alpha_talker": "npc"},
        {"run_eocs": {"id": "PF_HOME_invite_view", "effect": [{"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"}]}, "alpha_talker": "npc"},
        name_into("pf_say_a", "<npc_name>"),
        {"set_string_var": "none", "target_var": g("pf_inv_lead")},
        {"if": m("value_or(n_pf_is_leader, -1) == 1"), "then": [{"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_inv_lead")}]},
        {"if": {"and": [m("value_or(n_pf_is_leader, -1) == 0"), m("has_var(n_pf_leader)")]}, "then": [{"copy_var": {"npc_val": "pf_leader"}, "target_var": g("pf_inv_lead")}]},
        # playtest 3: someone who cooked you breakfast and kept your watch for nights still said "not ready to trust anyone"; strong warmth (50+) carries trust from 15
        {"if": {"and": [m("pf_read_w >= 35"), m("(pf_read_t >= 25) + (pf_read_w >= 50) * (pf_read_t >= 15) > 0")]},
         "then": [
             {"if": {"compare_string": [g("pf_inv_lead"), "none"]},
              "then": [{"run_eocs": "PF_HOME_join_one", "alpha_talker": "npc"}, line("invite_yes")],
              "else": [m("pf_hm_i = 0"), {"run_eocs": "PF_HOME_unroster_i", "condition": m("pf_hm_i < pf_band_n"), "iterations": 1000},
                       by_uid(["PF_HOME_join_band"], g("pf_inv_lead")),
                       # full run day 90: Easter said yes for Mitzi's band but wasn't on Mitzi's member list, and stayed out;
                       # whoever answered always comes
                       {"run_eocs": "PF_HOME_join_one", "alpha_talker": "npc"},
                       line("invite_band_yes"),
                       m("pf_bands_joined_total = value_or(pf_bands_joined_total, 0) + 1")]},
             m("pf_m_str_in = 70"), {"run_eocs": "PF_MK_welcomed", "beta_talker": "npc"}],
         # full run: three days of meals and the same "we don't know you" each time; a middle answer shows it's working
         "else": [{"if": m("pf_read_w < 20"), "then": [
                    # full run day 139: "We don't know you" right after the info screen said Janey "sees you as someone they know"
                    {"if": m("(pf_read_w + pf_read_t) / 2 >= 10"),
                     "then": [{"if": {"compare_string": [g("pf_inv_lead"), "none"]}, "then": [line("invite_known_one")], "else": [line("invite_known")]}],
                     "else": [{"if": {"compare_string": [g("pf_inv_lead"), "none"]}, "then": [line("invite_stranger_one")], "else": [line("invite_stranger")]}]}],
                   "else": [{"if": m("pf_read_w < 35"),
                             "then": [{"if": {"compare_string": [g("pf_inv_lead"), "none"]}, "then": [line("invite_warming_one")], "else": [line("invite_warming")]}],
                             "else": [line("invite_trust")]}]},
                  # 2026-10-17 (the user): "We don't know you" said nothing about how far there was to go.  The meter and what helps.
                  m("pf_bd_ok = 0"), {"run_eocs": "PF_PM_bond_read", "alpha_talker": "npc"},
                  {"if": m("pf_bd_ok == 1"), "then": [say("<global_val:pf_bd_bar> <global_val:pf_bd_word>  <global_val:pf_bd_hint>")]}]},
    ], "u = you, npc = the person you ask (People menu: Ask them to live with you).  They answer from their own view of you: warmth 35+ and trust 25+ (or warmth 50+ and trust 15+).  If they travel with an A-Life band, the whole band comes: it leaves the roster (the world no longer moves it) and everyone in it lives with you now.",
        condition=m(AT_HOME)),
    eoc("PF_HOME_unroster_i", [
        {"set_string_var": "pf_slot_<global_val:pf_hm_i>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"compare_string": [{"var_val": "ref"}, g("pf_inv_lead")]}, "then": [{"set_string_var": "none", "target_var": {"var_val": "ref"}}]},
        m("pf_hm_i += 1"),
    ]),
    eoc("PF_HOME_join_band", [
        {"if": {"not": {"compare_string": [{"u_val": "pf_member_%d" % k}, "none"]}}, "then": [by_uid(["PF_HOME_join_one"], {"u_val": "pf_member_%d" % k})]}
        for k in range(5)] + [{"run_eocs": "PF_HOME_join_one"}],
        "u = the band's leader (by unique id).  Everyone in the band moves in."),
    eoc("PF_HOME_join_one", [
        {"run_eocs": "PF_ID_ensure"},
        # v0.9: the band you travel with moves in with you (or you with them): you're no longer travelling
        {"if": m("(value_or(pf_tv_on, 0) == 1) * (value_or(u_pf_band, -1) == value_or(pf_tv_band, -2))"), "then": [m("pf_tv_on = 0")]},
        m("u_pf_tv_player = 0"), m("u_pf_based = 0"), m("u_pf_place = 0"),
        m("u_pf_resident = 1"), m("u_pf_resident_since = time('now')"),
        m("u_pf_is_leader = -1"), {"set_string_var": "none", "target_var": {"u_val": "pf_leader"}}, m("u_pf_band = 0"),
        m("u_pf_online = 1"), m("u_pf_settled = 0"), m("u_pf_pack = 1"),
        # day 152: "Marylin Whitmore unpacks at home: what's left of their food, and the things they carried all this way." (a day old)
        {"if": {"u_has_effect": "PF_infant"}, "then": [m("u_pf_pack = 0")]},
        {"run_eocs": "PF_HOME_role_pick"},
        {"if": {"u_has_trait": "PF_CHILD"}, "then": [m("u_pf_follow = 1"), {"run_eocs": "PF_FAM_list_kid"}]},
        m("pf_residents_n = value_or(pf_residents_n, 0) + 1"),
        m("u_pf_rc_t = time('now')"),
        # A-Life agents have a unique id (= pf_uid): keep a list, so a resident stranded outside the bubble can be brought home
        {"if": {"u_has_trait": "PF_AGENT"}, "then": [
            {"set_string_var": "pf_res_uid_<global_val:pf_res_un>", "target_var": ctx("ru"), "parse_tags": True},
            {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "ru"}}, m("pf_res_un = value_or(pf_res_un, 0) + 1"), m("u_pf_listed = 1")]},
        {"run_eocs": "PF_HOME_walk_home"},
    ], "u = someone moving in with you.  No longer in a band (pf_is_leader -1, pf_leader 'none': the death hook and succession leave the roster alone); children follow their family and are listed to grow up.  Once only (someone already living here is skipped).",
        condition=m("value_or(u_pf_resident, 0) == 0")),
    eoc("PF_HOME_walk_home", ANCHOR + [
        {"copy_var": {"u_val": "pf_anchor"}, "target_var": {"u_val": "pf_walk_to"}},
        {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("rand(6) - 3"), "y_adjust": m("rand(6) - 3")},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
    ], "u = a resident.  A walk order to a spot near home, or near their own house if their family joined the town (on-screen only; off-screen they stay where they were)."),
    eoc("PF_HOME_resident_tick", [
        # day 85: Mariano stood in the river 63 tiles out, inside the bubble but past a 60-tile roll-call
        {"u_run_npc_eocs": [{"id": "PF_HOME_rc_stamp", "condition": m("value_or(u_pf_resident, 0) == 1"), "effect": [
            m("u_pf_rc_t = time('now')"),
            # 2026-10-16: Lakia, taken in from a band as a child, still had pf_band 1 as a grown resident (band ids are
            # reused roster slots).  Someone who lives here belongs to no band.
            {"if": m("value_or(u_pf_band, 0) != 0"), "then": [m("u_pf_band = 0")]},
            # residents from before the list (session 6): listed the first time the roll-call sees them
            {"if": {"and": [{"u_has_trait": "PF_AGENT"}, m("value_or(u_pf_listed, 0) == 0")]}, "then": [
                m("u_pf_listed = 1"), {"set_string_var": "pf_res_uid_<global_val:pf_res_un>", "target_var": ctx("ru"), "parse_tags": True},
                {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "ru"}}, m("pf_res_un = value_or(pf_res_un, 0) + 1")]}]}],
         "local": True, "npc_range": 90},
        {"u_run_npc_eocs": ["PF_HOME_resident_one"], "local": True, "npc_range": 90},
    ], "Every 30 minutes, by day: residents in the bubble who have wandered more than 20 tiles from home walk back.  Not during the evening (seats), and never children who follow their family.",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m("time_since('midnight', 'unit': 'hours') >= 6"), m("time_since('midnight', 'unit': 'hours') < 19")]}),
    # full run day 100: Easter was left in the river 65 tiles out after the day-97 chase, outside the bubble, where nothing
    # moves NPCs; three days later still standing in the water.  Once a day, a resident the roll-call hasn't reached for a day
    # turns up at home (one teleport: a single map load, once a day at most).
    eoc("PF_HOME_stray_tick", [
        m(f"pf_st_day = {TODAY}"), m("pf_st_i = 0"),
        {"run_eocs": {"id": "PF_HOME_stray_i", "effect": [
            {"set_string_var": "pf_res_uid_<global_val:pf_st_i>", "target_var": ctx("ru"), "parse_tags": True},
            {"copy_var": {"var_val": "ru"}, "target_var": g("pf_st_uid")},
            {"u_run_npc_eocs": ["PF_HOME_stray_one"], "unique_ids": [g("pf_st_uid")], "local": False},
            m("pf_st_i += 1")]}, "condition": m("pf_st_i < value_or(pf_res_un, 0)"), "iterations": 40},
        # day 152: Marylin (a baby born in Golly's band) joined with her band but wasn't on the residents' list (only A-Life
        # agents were), and stayed 240 tiles out.  Children born or taken in here are on the family's kids list (unique ids);
        # the living ones are checked too.
        m("pf_st_i = 0"),
        {"run_eocs": {"id": "PF_HOME_stray_k", "effect": [
            {"set_string_var": "pf_kid_<global_val:pf_st_i>", "target_var": ctx("ku"), "parse_tags": True},
            {"copy_var": {"var_val": "ku"}, "target_var": g("pf_st_uid")},
            {"set_string_var": "pf_reg_<global_val:pf_st_uid>_dead", "target_var": ctx("kd"), "parse_tags": True},
            # the list has gaps ("none"; pf_kids_n counts the living, not the slots): all 30 slots
            {"if": {"and": [m("(value_or(v_kd, 0) == 0) * has_var(v_ku)"), {"not": {"compare_string": [g("pf_st_uid"), "none"]}}]}, "then": [
                {"u_run_npc_eocs": ["PF_HOME_stray_one"], "unique_ids": [g("pf_st_uid")], "local": False}]},
            m("pf_st_i += 1")]}, "condition": m("pf_st_i < 30"), "iterations": 30},
    ], "Hourly, by day, home: residents (A-Life agents, by unique id) who aren't here come home: at noon anyone out of the roll-call for a day; any hour, a newcomer who hasn't arrived after 4 hours.",
        recurrence="1 hours", **{"global": True},
        # full run day 182: with Dante 96 tiles out, "Deneen Bravo walks in at the gate…" (the roll call that marks people
        # seen only runs while you're home, so everyone looked missing).  Not while you're away (v0.7 pf_aw_state).
        condition={"and": [m(AT_HOME), m("time_since('midnight', 'unit': 'hours') >= 6"), m("time_since('midnight', 'unit': 'hours') < 22"),
                           m("value_or(pf_aw_state, 0) == 0")]}),
    eoc("PF_HOME_stray_one", ANCHOR + [
        m("u_pf_rc_t = time('now')"),
        {"copy_var": {"u_val": "pf_anchor"}, "target_var": {"u_val": "pf_tp"}},
        {"location_variable_adjust": {"u_val": "pf_tp"}, "x_adjust": m("rand(4) - 2"), "y_adjust": m("rand(4) - 2")},
        {"u_teleport": {"u_val": "pf_tp"}, "force_safe": True},
        name_into("pf_say_a"),
        # day 152: Consuelo's family said yes 12 map tiles out; they'd have turned up the next noon as "soaked through and
        # quiet, a day late.  Nobody asks where they've been."  A newcomer arrives that day, and is welcomed in.
        {"if": m("time('now') - value_or(u_pf_resident_since, 0) < time('2 d')"),
         "then": [{"if": {"u_has_effect": "PF_infant"}, "then": [line("newcomer_baby")],
                   "else": [{"if": {"u_has_trait": "PF_CHILD"}, "then": [line("newcomer_kid")], "else": [line("newcomer_home")]}]}],
         "else": [line("stray_home")]},
    ], "u = a resident who isn't home: out of the roll-call for a day (at noon), or a newcomer still on the road after 4 hours.",
        condition={"and": [m("value_or(u_pf_resident, 0) == 1"),
                           {"or": [{"and": [m("time('now') - value_or(u_pf_rc_t, 0) > time('1 d')"), m("time_since('midnight', 'unit': 'hours') >= 12"),
                                            m("time_since('midnight', 'unit': 'hours') < 13")]},
                                   {"and": [m("time('now') - value_or(u_pf_resident_since, 0) < time('2 d')"), m("time('now') - value_or(u_pf_rc_t, 0) > time('4 h')")]}]}]}),
    eoc("PF_HOME_resident_one", ANCHOR + [
        m("u_pf_rc_t = time('now')"),
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, u_pf_anchor) > 20"), "then": [{"run_eocs": "PF_HOME_walk_home"}]},
        {"if": {"and": [m("value_or(u_pf_pack, 0) == 1"), m("distance(u_pf_pos, u_pf_anchor) <= 20")]}, "then": [{"run_eocs": "PF_HOME_unpack"}]},
    ], condition={"and": [m("value_or(u_pf_resident, 0) == 1"), {"or": [m("value_or(u_pf_follow, 0) == 0"), m("value_or(u_pf_pack, 0) == 1")]}]}),
]

# ============================================================ THE WORLD (natural A-Life population)
def spawn_person(template, traits, kid=False):
    return [
        {"run_eocs": "PF_ALIFE_register_person"},
        {"u_spawn_npc": template, "unique_id": g("pf_person_uid"), "real_count": 1, "traits": traits,
         "target_var": g("pf_ws_at"), "min_radius": 0, "max_radius": 3},
        by_uid(["PF_ALIFE_store_uid", "PF_ID_ensure"], g("pf_person_uid")),
    ]
def link_member():
    return [{"copy_var": g("pf_person_uid"), "target_var": g("pf_link_member")}, {"run_eocs": "PF_BAND_link"}]
AGENT = ["PF_AGENT"]
KIDT = ["PF_AGENT", "SMALL2", "PF_CHILD"]
files["world.json"] = [
    eoc("PF_ENGINE_caps", [m("pf_eng_level = 0")], "Stock build: no engine patches.  The People First Engine mod overrides this (pf_eng_level = the patch level, e.g. 16 for items that answer PF_ROTTEN)."),
    eoc("PF_ENGINE_name_family_kid", [], "u = a child just spawned with a family (pf_ws_p1 = a parent's unique id).  Stock build: the generated name stays.  The People First Engine mod overrides this so the child carries the family's surname."),
    eoc("PF_WORLD_tick", [
        m("pf_wl = 0"), m("pf_wi = 0"),
        {"run_eocs": "PF_WORLD_count_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
        {"if": {"and": [m("pf_wl < value_or(pf_set_bands, 8)"), m("rand(9) < 4")]}, "then": [{"run_eocs": "PF_WORLD_spawn"}]},
    ], "Every 3 hours: if fewer bands are alive than the population setting (default 8), about one time in two and a half a new band appears at the edge of the bubble.",
        recurrence="3 hours", **{"global": True},
        condition={"and": [m("value_or(pf_alife_on, 1) == 1"), m("value_or(pf_set_bands, 8) > 0")]}),
    eoc("PF_WORLD_count_i", [
        {"set_string_var": "pf_slot_<global_val:pf_wi>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [m("pf_wl += 1")]},
        m("pf_wi += 1"),
    ]),
    eoc("PF_WORLD_spawn", [
        m("pf_ws_r = rand(8)"),
        m("pf_ws_kind = pf_ws_r >= 5 ? 1 : 0"),
        {"if": m("pf_ws_r == 8"), "then": [
            {"u_location_variable": g("pf_ws_at"), "furniture": "f_bed", "target_min_radius": 30, "target_max_radius": 60,
             "true_eocs": [{"id": "PF_WORLD_found_house", "effect": [m("pf_ws_kind = 2")]}]}]},
        {"if": m("pf_ws_kind < 2"), "then": [
            {"u_location_variable": g("pf_ws_at")},
            m("pf_ws_sx = rand(1) * 2 - 1"), m("pf_ws_sy = rand(1) * 2 - 1"),
            {"location_variable_adjust": g("pf_ws_at"), "x_adjust": m("pf_ws_sx * (40 + rand(14))"), "y_adjust": m("pf_ws_sy * rand(50)")}]},
        {"if": m("pf_ws_kind == 0"), "then": [{"run_eocs": "PF_WORLD_spawn_hunters"}], "else": [{"run_eocs": "PF_WORLD_spawn_family"}]},
        m("pf_world_spawned_total = value_or(pf_world_spawned_total, 0) + 1"),
        {"if": {"and": [m(CALM_LINES), m("rand(2) == 0")]}, "then": [line("distant")]},
    ], "u = avatar.  Hunters (5 in 9), a family on the move (3 in 9), or, one time in nine, a family settled in a house (a bed 30-60 tiles away; else on the move).  Bands on the move appear 40-54 tiles east or west of you, inside the bubble but out of sight; from there A-Life takes them."),
    eoc("PF_WORLD_spawn_hunters", spawn_person("PF_WANDERER", AGENT) + [
        {"copy_var": g("pf_person_uid"), "target_var": g("pf_band_new_leader")},
        {"run_eocs": "PF_ALIFE_register_band"},
        {"copy_var": g("pf_band_new_leader"), "target_var": g("pf_link_leader")},
    ] + spawn_person("PF_WANDERER", AGENT) + link_member() + [
        {"if": m("rand(1) == 0"), "then": spawn_person("PF_WANDERER", AGENT) + link_member()},
        m("pf_ws_task = 1"), by_uid(["PF_WORLD_init_leader"], g("pf_band_new_leader")),
    ], "u = avatar.  Two or three hunters: a leader and members in formation."),
    eoc("PF_WORLD_spawn_family", spawn_person("PF_SETTLER_F", AGENT) + [
        {"copy_var": g("pf_person_uid"), "target_var": g("pf_band_new_leader")},
        {"copy_var": g("pf_person_uid"), "target_var": g("pf_ws_p1")},
        {"run_eocs": "PF_ALIFE_register_band"},
        {"copy_var": g("pf_band_new_leader"), "target_var": g("pf_link_leader")},
    ] + [{"if": m("rand(5) > 0"), "then": spawn_person("PF_SETTLER_M", AGENT), "else": spawn_person("PF_SETTLER_F", AGENT)}] + link_member() + [
        {"copy_var": g("pf_person_uid"), "target_var": g("pf_ws_p2")},
        by_uid(["PF_WORLD_couple"], g("pf_ws_p1")),
        {"copy_var": g("pf_ws_p1"), "target_var": g("pf_ws_tmp")}, {"copy_var": g("pf_ws_p2"), "target_var": g("pf_ws_p1")}, {"copy_var": g("pf_ws_tmp"), "target_var": g("pf_ws_p2")},
        by_uid(["PF_WORLD_couple"], g("pf_ws_p1")),
        {"copy_var": g("pf_ws_p1"), "target_var": g("pf_ws_tmp")}, {"copy_var": g("pf_ws_p2"), "target_var": g("pf_ws_p1")}, {"copy_var": g("pf_ws_tmp"), "target_var": g("pf_ws_p2")},
        m("pf_ws_kids = 1 + rand(1)"), m("pf_ws_k = 0"),
        {"run_eocs": "PF_WORLD_family_kid", "condition": m("pf_ws_k < pf_ws_kids"), "iterations": 3},
        m("pf_ws_task = 0"), by_uid(["PF_WORLD_init_leader"], g("pf_band_new_leader")),
    ], "u = avatar.  A couple (partners or married; a mother and, five times in six, a father) and one or two children.  The children know who their parents are (orphan care, grief and the Web all work) and are listed to grow up."),
    eoc("PF_WORLD_family_kid", spawn_person("PF_KID", KIDT, kid=True) + link_member() + [
        by_uid(["PF_WORLD_kid_setup"], g("pf_person_uid")),
        m("pf_ws_k += 1"),
    ]),
    eoc("PF_WORLD_couple", [
        {"copy_var": g("pf_ws_p2"), "target_var": {"u_val": "pf_sweet"}}, m("u_pf_has_sweet = 1"),
        m("u_pf_rel_stage = 2 + rand(1)"), m("u_pf_sweet_since = time('now') - time('1 d') * (200 + rand(2000))"),
        m("u_pf_stage_since = u_pf_sweet_since"), m("u_pf_rom = 1"),
        # v0.7: drawn to their own spouse (the persona roll could pick an orientation that excludes them)
        {"set_string_var": "pf_reg_<global_val:pf_ws_p2>_g", "target_var": ctx("pg"), "parse_tags": True},
        {"if": m("(value_or(u_pf_orient, -1) != 2) * (value_or(u_pf_orient, -1) != value_or(v_pg, -1))"), "then": [m("u_pf_orient = value_or(v_pg, 2)")]},
        {"copy_var": g("pf_ws_p2"), "target_var": g("pf_m_other")}, m("pf_mv_role = 1"), m("pf_m_str_in = 85"), {"run_eocs": "PF_MV_wedding"},
    ], "u = one parent (by unique id), pf_ws_p2 = the other.  Together for years: partners or married, with a wedding memory."),
    eoc("PF_WORLD_kid_setup", [
        m("u_val('age') = 3 + rand(11)"),
        {"copy_var": g("pf_ws_p1"), "target_var": {"u_val": "pf_mom"}}, {"copy_var": g("pf_ws_p2"), "target_var": {"u_val": "pf_dad"}},
        {"set_string_var": "none", "target_var": {"u_val": "pf_guardian"}},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_ws_kid")},
        {"set_string_var": "pf_reg_<global_val:pf_ws_kid>_p1", "target_var": ctx("r1"), "parse_tags": True}, {"copy_var": g("pf_ws_p1"), "target_var": {"var_val": "r1"}},
        {"set_string_var": "pf_reg_<global_val:pf_ws_kid>_p2", "target_var": ctx("r2"), "parse_tags": True}, {"copy_var": g("pf_ws_p2"), "target_var": {"var_val": "r2"}},
        m("u_pf_adult = 0"), m("u_pf_rom = 0"), m("u_pf_rom_rolled = 1"), m("u_pf_follow = 0"),
        {"run_eocs": "PF_FAM_list_kid"},
        {"run_eocs": "PF_ENGINE_name_family_kid"},
        {"copy_var": g("pf_ws_p1"), "target_var": g("pf_m_other")}, m("pf_mv_role = 1"), m("pf_m_str_in = 70"), {"run_eocs": "PF_MV_parenting"},
        {"copy_var": g("pf_ws_p2"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_MV_parenting"},
    ], "u = a child just spawned (by unique id).  Age 3-13, both parents recorded (as the registry's p1/p2, so the Web shows them), never romantic, listed to grow up.  They travel in the band's formation, not as followers."),
    eoc("PF_WORLD_init_leader", [
        {"u_location_variable": {"u_val": "pf_vpos"}},
        {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_body"}},
        {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_wp_a"}},
        {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_wp_b"}},
        {"if": m("pf_ws_kind == 2"),
         "then": [m("u_pf_settled = 1"), {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_home"}},
                  m("pf_pl_join_only = 0"), {"run_eocs": "PF_PLACE_found_or_join"}],  # v0.9: a family found in a house has a place (gen_places)
         "else": [{"location_variable_adjust": {"u_val": "pf_wp_a"}, "overmap_tile": True, "x_adjust": m("(rand(1) * 2 - 1) * (3 + rand(6))"), "y_adjust": m("rand(12) - 6")},
                  {"location_variable_adjust": {"u_val": "pf_wp_b"}, "overmap_tile": True, "x_adjust": m("(rand(1) * 2 - 1) * (3 + rand(6))"), "y_adjust": m("rand(12) - 6")}]},
        {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_goal"}},
        m("u_pf_goal_is_b = 0"), m("u_pf_task = pf_ws_task"), m("u_pf_online = 1"), m("u_pf_quarry_spawned = 1"),
    ], "u = a new band's leader.  Hunters and families on the move patrol between two points 3-8 overmap tiles away (hunters hunt); a settled family's two points are both its house, so it stays home."),
]


# ============================================================ HOUSEHOLD (v0.4 pass 2: roles, chores, beds, unpacking)
ROLES = ["no particular job", "cook", "guard", "forager", "tinkerer", "carer", "herder", "farmer", "smith", "healer", "teacher"]  # herder/farmer: v0.5 Town (gen_town.py)
role_name = [{"if": m(f"value_or(u_pf_role, 0) == {i}"), "then": [{"set_string_var": r, "target_var": g("pf_say_b")}]} for i, r in enumerate(ROLES)]
NIGHT = "floor((time('now') - time('12 h')) / time('1 d'))"
bed_claims = []
for k in range(8):
    bed_claims.append({"if": {"and": [m(f"pf_bed_n > {k}"), m(f"distance(u_pf_bed, pf_bedc_{k}) < 1")]}, "then": [m("pf_bed_taken = 1")]})
files["household.json"] = [
    eoc("PF_HOME_role_pick", [
        m("_c = u_skill('cooking') * 2"),
        {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("_c += 2")]},
        m("_g = u_skill('melee') + u_skill('gun')"),
        {"if": {"u_has_trait": "PF_Q_PROUD"}, "then": [m("_g += 2")]},
        m("_f = u_skill('survival') * 2"),
        {"if": {"u_has_trait": "PF_T_LONER"}, "then": [m("_f += 2")]},
        m("_t = u_skill('fabrication') + u_skill('mechanics')"),
        m("_r = u_skill('firstaid') * 2"),
        {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("_r += 3")]},
        m("_h = (monsters_nearby('mon_cow', 'mon_goat', 'mon_chicken', 'radius': 25, 'location': pf_home_loc, 'attitude': 'friendly') > 0) * (u_skill('survival') + 1 + (u_has_trait('PF_Q_MOTHER_HEN') ? 2 : 0))"),
        m("_a = (value_or(pf_field_state, 0) > 0) * (u_skill('survival') + u_skill('cooking') + (u_has_trait('PF_Q_HATES_WASTE') ? 2 : 0))"),
        m("_s = u_skill('fabrication') * 2 + u_skill('mechanics') - 1"),
        m("_e = u_skill('firstaid') * 3 - 3"),
        # teacher only with a child who lives here (playtest 3: Myles became the teacher of a shelter with no children; pf_kids_n counts every kid in the world)
        m("pf_rp_kids = 0"),
        {"u_run_npc_eocs": [{"id": "PF_HOME_rp_kid", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, m("value_or(u_pf_resident, 0) == 1")]}, "effect": [m("pf_rp_kids += 1")]}],
         "local": True, "npc_range": 60},
        m("_k = (pf_rp_kids > 0) * (u_val('intelligence') - 8 + u_skill('speech'))"),
        m("_b = max(max(max(_c, _g), max(_f, _t)), max(max(_r, max(_h, _a)), max(_s, max(_e, _k))))"),
        m("u_pf_role = _b == _c ? 1 : (_b == _g ? 2 : (_b == _f ? 3 : (_b == _t ? 4 : (_b == _r ? 5 : (_b == _h ? 6 : (_b == _a ? 7 : (_b == _s ? 8 : (_b == _e ? 9 : 10))))))))"),
    ], "u = an adult who just moved in.  The job that fits their skills (and quirks): cook, guard, forager, tinkerer, carer, or (v0.5) herder when there are animals at home and farmer when there's a field.  Ties go in that order.",
        condition=ADULT),
    eoc("PF_HOME_role_next", [
        m("n_pf_role = value_or(n_pf_role, 0) % 10 + 1"),
        {"run_eocs": {"id": "PF_HOME_role_said", "effect": [name_into("pf_say_a")] + role_name}, "alpha_talker": "npc"},
        line("role_change"),
    ], "u = you, npc = someone who lives with you (People menu: Ask them to take a different job).  Cycles cook, guard, forager, tinkerer, carer, herder, farmer, smith, healer, teacher."),
    eoc("PF_HOME_roster", [
        m("pf_ro_n = 0"),
        {"u_run_npc_eocs": ["PF_HOME_roster_one"], "local": True, "npc_range": 60},
        {"if": m("pf_ro_n == 0"), "then": [line("roster_none")]},
    ], "u = you (Home: Who does what).  One line per person who lives with you and is nearby."),
    eoc("PF_HOME_roster_one", [m("pf_ro_n += 1"), name_into("pf_say_a")] + role_name + [
        {"if": {"and": [m("value_or(pf_chief_set, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_chief_uid")]}]},
         "then": [{"set_string_var": "<global_val:pf_say_b>, and chief", "target_var": g("pf_say_b"), "parse_tags": True}],
         "else": [{"if": m("(value_or(pf_cn_n, 0) > 0) * (value_or(u_pf_cn_term, -1) == value_or(pf_cn_term, -2))"),
                   "then": [{"set_string_var": "<global_val:pf_say_b>, and on the council", "target_var": g("pf_say_b"), "parse_tags": True}]}]},
        {"if": {"u_has_effect": "sleep"}, "then": [{"set_string_var": "<global_val:pf_say_b> (asleep)", "target_var": g("pf_say_b"), "parse_tags": True}]},
        line("roster")],
        condition={"and": [m("value_or(u_pf_resident, 0) == 1"), ADULT]}),
    # full run day 89: the stores (lamp, water, pot) ran inside the 3-hourly chore tick, which only runs when it's calm; at Kinfold
    # it rarely was, and a day and a half went by without a pot.  The cook keeps the stores on their own hourly tick, alarms or not.
    eoc("PF_HOME_supply_tick", [
        m("pf_sup_done = 0"),
        {"u_run_npc_eocs": ["PF_HOME_supply_one"], "local": True, "npc_range": 60},
        {"if": {"and": [m("pf_sup_done == 0"), m("value_or(pf_ck_day, -1) != floor(time('now') / time('1 d'))")]}, "then": [
            m("pf_ck_day = floor(time('now') / time('1 d'))"), {"run_eocs": "PF_HOME_cook_fill"}]},
    ], "Every hour, 06:00-21:00: the first cook found at home keeps the stores (a candle by them each week, a jug of water a day, a pot every 8 hours).  If nobody who lives here is the cook (once a day), someone takes it on.",
        recurrence="1 hours", **{"global": True},
        condition={"and": [m(AT_HOME), m("time_since('midnight', 'unit': 'hours') >= 6"), m("time_since('midnight', 'unit': 'hours') < 21")]}),
    eoc("PF_HOME_supply_one", ANCHOR + [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, u_pf_anchor) <= 25"), "then": [
            m("pf_sup_done = 1"), name_into("pf_say_a"),
            # full run: at night the stores were out of sight and reach; you went to bed thirsty with 60 servings of water in
            # the room.  The cook keeps a candle burning by the stores (a new one each week).
            # full run day 150: eight burning candles at the stores (one a week; a candle on the map never burns down).  A new one
            # only if none is lit there.
            {"if": m("time('now') - value_or(pf_lamp_t, 0) >= time('7 d')"), "then": [
                m("pf_lamp_t = time('now')"), m("pf_lamp_n = 0"),
                {"u_map_run_item_eocs": "all", "loc": g("pf_stores_loc"), "min_radius": 0, "max_radius": 2, "search_data": [{"id": "candle_lit"}],
                 "true_eocs": [{"id": "PF_HOME_lamp_count", "effect": [m("pf_lamp_n += 1")]}]},
                {"if": m("pf_lamp_n == 0"), "then": [{"map_spawn_item": "candle_lit", "loc": g("pf_stores_loc")}, line("chore_lamp")]}]},
            # playtest 3 / full run: 50 bowls in three days with two cooks and a pot every 6 h, and only you eat (no_npc_food).
            # Water once a day (a jug, about what one player drinks).
            # v0.8: the cook checks the stores first (full run: soup and eggs rotting on the floor, a bowl per serving piling up)
            {"run_eocs": "PF_STORES_ensure"},
            m("pf_ck_bowls = 0"), m("pf_ck_jugs = 0"), {"run_eocs": "PF_ENGINE_caps"},
            # engine patch 16: a bowl gone rotten isn't a meal waiting (it blocked the next pot); the tidy throws it out
            {"u_map_run_item_eocs": "all", "loc": g("pf_stores_loc"), "min_radius": 0, "max_radius": 2,
             "search_data": [{"id": "ceramic_bowl", "condition": {"and": [m("n_weight() >= 405000"), {"or": [
                 m("value_or(pf_eng_level, 0) < 16"), {"not": {"npc_has_flag": "PF_ROTTEN"}}]}]}}],
             "true_eocs": [{"id": "PF_HOME_ck_bowl", "effect": [m("pf_ck_bowls += 1")]}]},
            {"u_map_run_item_eocs": "all", "loc": g("pf_stores_loc"), "min_radius": 0, "max_radius": 2,
             "search_data": [{"id": "jug_plastic", "condition": m("n_weight() >= 1000000")}],
             "true_eocs": [{"id": "PF_HOME_ck_jug", "effect": [m("pf_ck_jugs += 1")]}]},
            {"if": m("(time('now') - value_or(pf_water_last, 0) >= time('1 d')) * (pf_ck_jugs < 3)"), "then": [
                m("pf_water_last = time('now')"),
                {"map_spawn_item": "water_clean", "loc": g("pf_stores_loc"), "container": "jug_plastic", "count": 8}]},
            # day 84: vegetable soup is 34 kcal a bowl; the player went hungry beside a pot of it and eight bowls rotted.
            # day 88: one pot of 2 bowls a day was about 500 kcal.  A pot is 3 servings of stew, meat soup or egg soup, every 8 hours.
            {"if": m("(time('now') - value_or(pf_pot_last, 0) >= time('8 h')) * (pf_ck_bowls < 4)"), "then": [
                m("pf_pot_last = time('now')"), m("_s = rand(2)")] + [
                # day 90: two servings of three sisters stew don't fit one ceramic bowl ("pocket unacceptable", an in-game
                # error); one serving per bowl for every soup
                {"if": m(f"_s == {k}"), "then": [{"map_spawn_item": soup, "loc": g("pf_stores_loc"), "container": "ceramic_bowl", "count": 1}] * 3}
                for k, soup in enumerate(["soup_three_sisters", "soup_meat", "soup_woods_egg"])]}]},
    ], "u = someone who lives with you.  The first cook near home keeps the stores.",
        condition={"and": [m("pf_sup_done == 0"), m("value_or(u_pf_resident, 0) == 1"), m("value_or(u_pf_role, 0) == 1"), ADULT,
                           {"not": {"u_has_effect": "sleep"}}]}),
    # full run day 104: Isaias, the cook, died; Henriette, Mitzi and Easter were all guards (jobs go by skill alone), so the
    # pot stopped and the stores ran down to jerky and pemmican.  Nobody noticed for three days.
    eoc("PF_HOME_cook_fill", [
        m("pf_ck_n = 0"),
        {"u_run_npc_eocs": [{"id": "PF_HOME_ck_count", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), m("value_or(u_pf_role, 0) == 1"), ADULT]},
                             "effect": [m("pf_ck_n += 1")]}], "local": True, "npc_range": 60},
        {"if": m("pf_ck_n == 0"), "then": [
            m("pf_ck_best = -1"),
            {"u_run_npc_eocs": [{"id": "PF_HOME_ck_cand", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), ADULT]}, "effect": [
                m("_s = u_skill('cooking') * 2 + rand(2)"),
                {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("_s += 2")]},
                {"if": m("_s > pf_ck_best"), "then": [m("pf_ck_best = _s"), {"u_set_talker": g("pf_ck_who")}]}]}], "local": True, "npc_range": 60},
            {"if": m("pf_ck_best >= 0"), "then": [
                {"run_eocs": {"id": "PF_HOME_ck_take", "effect": [m("u_pf_role = 1"), name_into("pf_say_a")]}, "alpha_talker": g("pf_ck_who")},
                line("cook_fill")]}]},
    ], "u = you, at home.  Nobody who lives here is the cook: whoever cooks best (or a mother hen) takes the pot over, and says so."),
    eoc("PF_HOME_chore_tick", [
        m("pf_ch_l = 0")] + [m(f"pf_ch_said_{r} = 0") for r in range(1, 6)] + [
        {"u_location_variable": g("pf_hm_av")},
        m("pf_ch_av = distance(pf_hm_av, pf_home_loc) <= 30"),
        {"run_eocs": "PF_THREAT_scan"},
        {"if": m("pf_threat == 0"), "then": [{"u_run_npc_eocs": ["PF_HOME_chore_one"], "local": True, "npc_range": 60}]},
    ], "Every 3 hours, 08:00-18:00, when it's calm: everyone who lives with you and is within 25 tiles of home does their job.  The cook leaves soup at home, the forager brings back berries or mushrooms, the guard walks the edge of the place, the tinkerer fixes things, the carer looks after the children.  At most three lines each time, and only if you're home.",
        recurrence="3 hours", **{"global": True},
        condition={"and": [m(AT_HOME), m("time_since('midnight', 'unit': 'hours') >= 8"), m("time_since('midnight', 'unit': 'hours') < 18"), m("(value_or(pf_law_rest, 0) == 1) * (floor(time('now') / time('1 d')) % 7 == 2) == 0")]}),
    eoc("PF_HOME_chore_one", ANCHOR + [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("value_or(u_pf_role, 0) == 0"), "then": [{"run_eocs": "PF_HOME_role_pick"}]},
        {"if": m("distance(u_pf_pos, u_pf_anchor) <= 25"), "then": [
            name_into("pf_say_a"),
            m("pf_ch_say = pf_ch_av * (pf_ch_l < 3) * (value_or(pf_set_chatter, 1) == 1) * (time('now') >= value_or(u_pf_mourn_until, 0))"),
            {"if": m("u_pf_role == 1"), "then": [
                # playtest 3: two cooks, four rounds a day: "burned the soup again" twice in an afternoon.  At most once in 3 days.
                {"if": {"and": [m("rand(5) == 0"), m("time('now') - value_or(pf_burnt_last, 0) >= time('3 d')")]},
                 "then": [{"run_eocs": "PF_HOME_burnt"}],
                 # playtest 3: two cooks, four rounds a day, and nobody but you eats (no_npc_food): 50 bowls in three days, and
                 # the water ran out.  One pot every 6 hours for the household, and whoever cooks fetches water too.
                 # full run: one cook, a pot every 6 h: 53 servings of water and 9 bowls of soup by day 68, and only you eat.
                 # Soup every 12 h, water once a day (a jug, about what one player drinks).
                 # full run day 89: the stores (lamp, water, pot) moved to their own hourly tick (PF_HOME_supply_tick); this
                 # tick only runs when it's calm, and at Kinfold it rarely was: a day and a half without a pot.
                 "else": [{"if": m("rand(1) == 0"), "then": chore_line(1, "chore_cook", 4)}]}]},
            {"if": m("u_pf_role == 2"), "then": [
                {"copy_var": g("pf_home_loc"), "target_var": {"u_val": "pf_walk_to"}},
                {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("(rand(1) * 2 - 1) * 12"), "y_adjust": m("rand(24) - 12")},
                {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
                {"if": m("rand(2) == 0"), "then": chore_line(2, "chore_guard", 3)}]},
            {"if": m("u_pf_role == 3"), "then": [
                m("_k = rand(3)"),
                {"if": m("_k == 0"), "then": [{"map_spawn_item": "blueberries", "loc": g("pf_stores_loc"), "count": 4}, {"set_string_var": "an armful of blueberries", "target_var": g("pf_say_b")}]},
                {"if": m("_k == 1"), "then": [{"map_spawn_item": "raspberries", "loc": g("pf_stores_loc"), "count": 4}, {"set_string_var": "a hat full of raspberries", "target_var": g("pf_say_b")}]},
                {"if": m("_k == 2"), "then": [{"map_spawn_item": "mushroom", "loc": g("pf_stores_loc"), "count": 3}, {"set_string_var": "a bag of mushrooms (they swear they're the good kind)", "target_var": g("pf_say_b")}]},
                {"if": m("_k == 3"), "then": [{"map_spawn_item": "acorns", "loc": g("pf_stores_loc"), "count": 6}, {"set_string_var": "a pocketful of acorns", "target_var": g("pf_say_b")}]},
                {"if": m("rand(1) == 0"), "then": chore_line(3, "chore_forage", 3)}]},
            {"if": {"and": [m("u_pf_role == 4"), m("rand(1) == 0")]}, "then": chore_line(4, "chore_tinker", 3)},
            {"if": m("u_pf_role == 5"), "then": [
                m("pf_ch_kid = 0"),
                {"u_run_npc_eocs": [{"id": "PF_HOME_carer_kid", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, m("pf_ch_kid == 0")]},
                                     "effect": [m("pf_ch_kid = 1"), name_into("pf_say_b"), {"u_set_talker": g("pf_ch_kidwho")}]}], "local": True, "npc_range": 15},
                {"if": m("pf_ch_kid == 1"), "then": [m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_parenting", "beta_talker": g("pf_ch_kidwho")},
                                                    {"if": m("pf_ch_say"), "then": [m("pf_ch_l += 1"), line("chore_carer")]}]}]},
            {"if": {"and": [m("u_pf_role == 6"), m("pf_ch_say"), m("rand(1) == 0"),
                            m("monsters_nearby('mon_cow', 'mon_goat', 'mon_chicken', 'radius': 25, 'location': pf_home_loc, 'attitude': 'friendly') > 0")]},
             "then": [m("pf_ch_l += 1"), {"run_eocs": "PF_SAY_town", "alpha_talker": "avatar", "variables": {"line": "chore_herder"}}]},
            {"if": {"and": [m("u_pf_role == 7"), m("pf_ch_say"), m("rand(1) == 0"), m("value_or(pf_field_state, 0) == 2")]},
             "then": [m("pf_ch_l += 1"), {"run_eocs": "PF_SAY_town", "alpha_talker": "avatar", "variables": {"line": "chore_farmer"}}]},
            {"if": m("rand(7) == 0"), "then": [{"run_eocs": "PF_HOME_practice"}]},
            m("pf_chores_total = value_or(pf_chores_total, 0) + 1"),
            {"if": m("value_or(pf_law_tithe, 0) == 1"), "then": [{"run_eocs": "PF_KEEP_tithe_one"}]}]},
    ], "u = someone who lives with you.  Mourners still do their job, quietly (no line).  Residents from before v0.4 pass 2 have no job yet; they get one here (playtest 2).", condition={"and": [m("value_or(u_pf_resident, 0) == 1"), ADULT]}),
    eoc("PF_HOME_bed_tick", [
        m("pf_night = %s" % NIGHT),
        {"if": m("value_or(pf_bed_night, -1) != pf_night"), "then": [m("pf_bed_night = pf_night"), m("pf_bed_n = 0"),
            {"u_location_variable": g("pf_hm_av")},
            {"if": {"and": [m("distance(pf_hm_av, pf_home_loc) <= 30"), m(CALM_LINES)]}, "then": [line("bedtime")]}]},
        {"u_run_npc_eocs": ["PF_HOME_bed_one"], "local": True, "npc_range": 60},
    ], "Every 30 minutes from 22:00 to 05:00: everyone who lives with you goes to bed.  Each claims a free bed within 20 tiles (no two in one bed), or makes do on the floor near home, and falls asleep once there.",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), {"or": [m("time_since('midnight', 'unit': 'hours') >= 22"), m("time_since('midnight', 'unit': 'hours') < 5")]}]}),
    eoc("PF_HOME_bed_one", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("value_or(u_pf_bed_night, -1) != pf_night"),
         "then": [m("u_pf_bed_night = pf_night"),
                  # v0.8: everyone keeps their own corner (a bed, or a patch of floor) from night to night
                  {"run_eocs": "PF_HOUSE_corner_assign"},
                  {"copy_var": {"u_val": "pf_corner"}, "target_var": {"u_val": "pf_bed"}},
                  {"copy_var": {"u_val": "pf_bed"}, "target_var": {"u_val": "pf_walk_to"}},
                  {"u_set_guard_pos": {"u_val": "pf_walk_to"}}],
         "else": [{"if": {"and": [m("distance(u_pf_pos, u_pf_bed) <= 1"), {"not": {"u_has_effect": "sleep"}}]},
                   "then": [{"u_add_effect": "sleep", "duration": "6 hours"}]}]},
    ], "u = someone who lives with you (adults and grown children; small children follow their family).  A family that joined the town sleeps in its own house.  Whoever is on the town watch stays up.",
        condition={"and": [m("value_or(u_pf_resident, 0) == 1"), m("value_or(u_pf_follow, 0) == 0"), {"not": ON_WATCH}]}),
    eoc("PF_HOME_unpack", [
        m("u_pf_pack = 0"),
        {"if": {"u_has_effect": "PF_infant"}, "then": [{"run_eocs": "PF_HOME_unpack_none"}], "else": [{"run_eocs": "PF_HOME_unpack_do"}]},
    ], "u = someone who just arrived home for the first time.  A baby has nothing to unpack."),
    eoc("PF_HOME_unpack_none", [], "A baby arriving: nothing to unpack."),
    eoc("PF_HOME_unpack_do", [
        # v0.8: the food goes in with the stores; their own things go to their corner
        {"run_eocs": "PF_STORES_ensure"},
        {"if": {"u_has_trait": "PF_CHILD"},
         "then": [{"map_spawn_item": "candy", "loc": g("pf_stores_loc"), "count": 2}, {"map_spawn_item": "marble", "loc": g("pf_home_loc"), "count": 3}],
         "else": [{"map_spawn_item": "can_beans", "loc": g("pf_stores_loc"), "count": 2}, {"map_spawn_item": "jerky", "loc": g("pf_stores_loc"), "count": 2},
                  {"run_eocs": "PF_HOUSE_corner_assign"},
                  {"if": m("rand(1) == 0"),
                   "then": [{"map_spawn_item": "blanket", "loc": {"u_val": "pf_corner"}}, {"map_spawn_item": "matches", "loc": {"u_val": "pf_corner"}}],
                   "else": [{"map_spawn_item": "bandages", "loc": {"u_val": "pf_corner"}, "count": 3}, {"map_spawn_item": "aspirin", "loc": {"u_val": "pf_corner"}}]}]},
        {"if": {"and": [cooldown_ok_c("pf_unpack_line", "10 m"), m(CALM_LINES)]}, "then": [m("pf_unpack_line = time('now')"), name_into("pf_say_a"), line("unpack")]},
    ], "u = someone who just arrived home for the first time.  They unpack what they carried: canned beans and jerky, plus a blanket and matches or bandages and aspirin (children: candy and marbles).  Concrete items, because an item group via use_item_group raises 'Missing item definition' in 0.I.  Waits until they're home, so nothing spawns on an unloaded map."),
]

# ============================================================ RUMORS (concept §5.6 'Seeing it from afar': true, because it comes from the simulation)
DIRS = [("pf_rm_dx > 2 * abs(pf_rm_dy)", "east"), ("-pf_rm_dx > 2 * abs(pf_rm_dy)", "west"), ("pf_rm_dy > 2 * abs(pf_rm_dx)", "south"), ("-pf_rm_dy > 2 * abs(pf_rm_dx)", "north"),
        ("(pf_rm_dx > 0) * (pf_rm_dy > 0)", "southeast"), ("(pf_rm_dx < 0) * (pf_rm_dy > 0)", "southwest"), ("(pf_rm_dx > 0) * (pf_rm_dy < 0)", "northeast"), ("(pf_rm_dx < 0) * (pf_rm_dy < 0)", "northwest")]
dir_eff = [{"set_string_var": "somewhere", "target_var": g("pf_rm_dir")}]
for cond, word in DIRS[4:] + DIRS[:4]:  # diagonals first, then the cardinal tests, which win when they apply
    dir_eff.append({"if": m(cond), "then": [{"set_string_var": word, "target_var": g("pf_rm_dir")}]})
RM = 6
files["rumors.json"] = [
    eoc("PF_HOME_rumor_try", [{"run_eocs": "PF_HOME_rumor_do"}],
        "u = you, at tonight's evening (called from the evening's beat).  About one evening in two, at most every 12 hours, if you're there.",
        condition={"and": [m("value_or(pf_fire_av_here, 0) == 1"), m("pf_fire_n > 0"), m(CALM_LINES), m("value_or(pf_band_n, 0) > 0"),
                           {"or": [m("value_or(pf_rm_force, 0) == 1"), {"and": [m("rand(1) == 0"), cooldown_ok_c("pf_rumor_last", "12 h")]}]}]}),
    eoc("PF_HOME_rumor_do", [
        m("pf_rumor_last = time('now')"),
        m("pf_rm_ok = 0"), {"u_location_variable": g("pf_rm_av")},
        m("pf_rm_s = rand(max(value_or(pf_band_n, 1) - 1, 0))"), m("pf_rm_j = 0"),
        {"run_eocs": "PF_HOME_rumor_pick", "condition": {"and": [m("pf_rm_j < value_or(pf_band_n, 0)"), m("pf_rm_ok == 0")]}, "iterations": 1000},
        {"if": m("pf_rm_ok == 0"), "then": [m("pf_rm_none = 1")], "else": [m("pf_rm_none = 0")]},
        {"if": m("pf_rm_ok == 1"), "then": [
            {"if": m("pf_rm_ok == 1"), "then": [
                m("pf_rm_dx = pf_rm_pos.x - pf_rm_av.x"), m("pf_rm_dy = pf_rm_pos.y - pf_rm_av.y"),
                m("pf_rm_km = round(pf_rm_d / 100) / 10"),
            ] + dir_eff + [
                m("pf_rm_sp = rand(max(pf_fire_n - 1, 0))"),
                {"set_string_var": "pf_fire_c_<global_val:pf_rm_sp>", "target_var": ctx("sp"), "parse_tags": True},
                {"run_eocs": {"id": "PF_HOME_rumor_speaker", "effect": [name_into("pf_say_a")]}, "alpha_talker": {"var_val": "sp"}},
                {"set_string_var": "<global_val:pf_say_a> mentions <global_val:pf_rm_what>, about <global_val:pf_rm_km> km <global_val:pf_rm_dir> of here.", "target_var": g("pf_rm_text"), "parse_tags": True},
                line("rumor"),
                m("pf_rm_k = value_or(pf_rumors_n, 0) %% %d" % RM),
                {"set_string_var": "pf_rumor_<global_val:pf_rm_k>", "target_var": ctx("rk"), "parse_tags": True},
                {"copy_var": g("pf_rm_text"), "target_var": {"var_val": "rk"}},
                {"set_string_var": "pf_rumor_t_<global_val:pf_rm_k>", "target_var": ctx("rt"), "parse_tags": True},
                m("v_rt = time('now')"),
                m("pf_rumors_n = value_or(pf_rumors_n, 0) + 1")]}]},
    ], "u = you.  Someone at the evening mentions a real band they've heard of: what kind, how many, how far and which way.  It's true: it comes from the simulation (the band's virtual position).  Bands closer than 80 tiles don't count (you can see those)."),
    eoc("PF_HOME_rumor_pick", [
        m("pf_rm_i = (pf_rm_s + pf_rm_j) % value_or(pf_band_n, 1)"),
        {"set_string_var": "pf_slot_<global_val:pf_rm_i>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [
            by_uid(["PF_HOME_rumor_band"], {"var_val": "ref"}),
            {"if": m("pf_rm_ok == 1"), "then": [m("pf_rm_d = distance(pf_rm_av, pf_rm_pos)"), {"if": m("pf_rm_d < 80"), "then": [m("pf_rm_ok = 0")]}]},
            {"if": m("pf_rm_ok == 1"), "then": [by_uid([{"id": "PF_HOME_rumor_mark", "effect": [m("u_pf_rumor_t = time('now')")]}], {"var_val": "ref"})]}]},
        m("pf_rm_j += 1"),
    ], "Tries roster slot (start + j): a living band at least 80 tiles away (closer ones you can see for yourself), not talked about in the last 3 days."),
    eoc("PF_HOME_rumor_band", [
        m("pf_rm_ok = 1"),
        # playtest 3: the same hunters "0.2 km northeast" two nights running; a band that was talked about rests 3 days
        {"if": {"and": [m("value_or(pf_rm_force, 0) == 0"), m("time('now') - value_or(u_pf_rumor_t, 0) < time('3 d')")]}, "then": [m("pf_rm_ok = 0")]},
        {"if": {"and": [m("value_or(u_pf_online, 0) == 0"), m("has_var(u_pf_vpos)")]},
         "then": [{"copy_var": {"u_val": "pf_vpos"}, "target_var": g("pf_rm_pos")}],
         "else": [{"u_location_variable": g("pf_rm_pos")}]},
        m("pf_rm_n = value_or(u_pf_band_size, 0) + 1"),
        {"set_string_var": "<global_val:pf_rm_n> hunters on the move", "target_var": g("pf_rm_what"), "parse_tags": True},
        {"if": m("value_or(u_pf_task, 1) == 0"), "then": [{"set_string_var": "a family on the road, kids and all", "target_var": g("pf_rm_what")}]},
        {"if": m("value_or(u_pf_settled, 0) == 1"), "then": [{"set_string_var": "a family who've made a home for themselves", "target_var": g("pf_rm_what")}]},
        # v0.7 (gen_away.py): what happened to them on the road, for a week
        {"if": m("has_var(u_pf_trouble_t) * (time('now') - value_or(u_pf_trouble_t, 0) < time('7 d'))"), "then": [
            {"if": m("value_or(u_pf_trouble_kind, 0) == 3"), "then": [{"set_string_var": "<global_val:pf_rm_what>, who lost one of theirs to the dead on the road", "target_var": g("pf_rm_what"), "parse_tags": True}]},
            {"if": m("value_or(u_pf_trouble_kind, 0) == 2"), "then": [{"set_string_var": "<global_val:pf_rm_what>, one of them still limping from a run-in with the dead", "target_var": g("pf_rm_what"), "parse_tags": True}]},
            {"if": m("value_or(u_pf_trouble_kind, 0) == 1"), "then": [{"set_string_var": "<global_val:pf_rm_what>, jumpy after a run-in with the dead", "target_var": g("pf_rm_what"), "parse_tags": True}]}]},
    ], "u = a band's leader (by unique id, anywhere).  Off-screen its position is data (u_pf_vpos), so this never loads a map."),
    eoc("PF_HOME_rumors", [
        m("pf_rl_n = 0"),
    ] + [x for k in range(RM) for x in (
        m(f"pf_rl_k = (value_or(pf_rumors_n, 0) - 1 - {k} + {RM} * 10) % {RM}"),
        {"if": m(f"value_or(pf_rumors_n, 0) > {k}"), "then": [
            {"set_string_var": "pf_rumor_<global_val:pf_rl_k>", "target_var": ctx("rk"), "parse_tags": True},
            {"set_string_var": "pf_rumor_t_<global_val:pf_rl_k>", "target_var": ctx("rt"), "parse_tags": True},
            {"copy_var": {"var_val": "rk"}, "target_var": g("pf_rl_text")},
            m("pf_rl_ago = floor((time('now') - value_or(v_rt, 0)) / time('1 d'))"),
            {"if": m("pf_rl_ago == 0"), "then": [line("rumor_list_today")], "else": [line("rumor_list")]}, m("pf_rl_n += 1")]})] + [
        {"if": m("pf_rl_n == 0"), "then": [line("rumor_none")]},
    ], "u = you (Home: What people have heard).  The last six rumors, newest first, with how many days ago."),
]
files["world.json"] += [
    eoc("PF_WORLD_drift_tick", [
        m("pf_wi = 0"),
        {"run_eocs": "PF_WORLD_drift_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
    ], "Once a day: bands change their lives a little.  A band may make camp for a few days (one day in four), a family on the road may find a place and settle (one day in seven), hunters may move to new grounds (one day in two).  Pure data: waypoints move, nothing loads.",
        recurrence="1 days", **{"global": True}, condition=m("value_or(pf_alife_on, 1) == 1")),
    eoc("PF_WORLD_drift_i", [
        {"set_string_var": "pf_slot_<global_val:pf_wi>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [by_uid(["PF_WORLD_drift_one"], {"var_val": "ref"})]},
        m("pf_wi += 1"),
    ]),
    eoc("PF_WORLD_drift_one", [
        {"if": m("value_or(u_pf_online, 0) == 1"), "then": [{"u_location_variable": {"u_val": "pf_vpos"}}]},
        # 2026-10-17 (the user: "all npcs are just missed opportunities flowing down a river"): bands make camp now and then.
        # A camping band (u_pf_camp_until; both waypoints are the camp, people menu PF_WHERE_make_camp) stays put, and
        # word along the road says so; when the camp ends it goes back on the road from there.
        {"if": m("value_or(u_pf_camp_until, 0) <= time('now')"), "then": [
            {"if": m("value_or(u_pf_camp_until, 0) > 0"), "then": [
                m("u_pf_camp_until = 0"),
                {"copy_var": {"u_val": "pf_camp"}, "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": {"u_val": "pf_camp"}, "target_var": {"u_val": "pf_wp_b"}},
                {"location_variable_adjust": {"u_val": "pf_wp_a"}, "overmap_tile": True, "x_adjust": m("(rand(1) * 2 - 1) * (3 + rand(6))"), "y_adjust": m("rand(12) - 6")},
                {"location_variable_adjust": {"u_val": "pf_wp_b"}, "overmap_tile": True, "x_adjust": m("(rand(1) * 2 - 1) * (3 + rand(6))"), "y_adjust": m("rand(12) - 6")},
                {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_goal"}}, m("u_pf_goal_is_b = 0"),
                m("pf_world_camps_ended_total = value_or(pf_world_camps_ended_total, 0) + 1")]},
            m("pf_dr_camped = 0"),
            # v0.9 (gen_places): a band on the road near a place people made may drift into it, one day in four (families
            # settle there, hunters hunt out of it).  Hunters already based at a place keep their grounds.
            {"if": {"and": [m("value_or(u_pf_based, 0) == 0"), m("rand(3) == 0")]}, "then": [
                m("pf_pl_join_only = 1"), {"run_eocs": "PF_PLACE_found_or_join"}, m("pf_dr_camped = pf_pl_joined")]},
            {"if": m("value_or(u_pf_based, 0) == 1"), "then": [m("pf_dr_camped = 1")]},
            {"if": {"and": [m("pf_dr_camped == 0"), m("rand(3) == 0"), m("value_or(u_pf_joining, 0) == 0")]}, "then": [
                m("pf_dr_camped = 1"),
                {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_camp"}},
                {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_wp_b"}},
                {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_goal"}}, m("u_pf_goal_is_b = 0"),
                m("u_pf_camp_until = time('now') + time('1 d') * (4 + rand(6))"),
                m("pf_world_camps_total = value_or(pf_world_camps_total, 0) + 1")]},
            {"if": {"and": [m("pf_dr_camped == 0"), m("value_or(u_pf_task, 1) == 0"), m("rand(6) == 0"),
                            {"or": [m("value_or(pf_home_set, 0) == 0"), m("distance(u_pf_vpos, pf_home_loc) > 60")]}]}, "then": [
                m("u_pf_settled = 1"), {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_home"}},
                {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_wp_b"}},
                {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_goal"}},
                m("pf_world_settled_total = value_or(pf_world_settled_total, 0) + 1"),
                # v0.9: settling means a place: the nearest one with room within 8 map tiles, else a new one of their own
                m("pf_pl_join_only = 0"), {"run_eocs": "PF_PLACE_found_or_join"}, m("pf_dr_camped = 1")]},
            {"if": {"and": [m("pf_dr_camped == 0"), m("value_or(u_pf_task, 1) == 1"), m("rand(2) == 0")]}, "then": [
                m("pf_dr_x = rand(12) - 6"), m("pf_dr_y = rand(12) - 6"),
                {"location_variable_adjust": {"u_val": "pf_wp_a"}, "overmap_tile": True, "x_adjust": m("pf_dr_x"), "y_adjust": m("pf_dr_y")},
                {"location_variable_adjust": {"u_val": "pf_wp_b"}, "overmap_tile": True, "x_adjust": m("pf_dr_x"), "y_adjust": m("pf_dr_y")},
                m("pf_world_moved_total = value_or(pf_world_moved_total, 0) + 1")]}]},
    ], "u = a band's leader (by unique id).  A camping band stays put; one day in four a band on the road makes camp where it is for 4-10 days.", condition=m("value_or(u_pf_settled, 0) == 0")),
]

# ============================================================ FRICTION, LEAVING, PRACTICE, NEIGHBORS (v0.4 pass 3)
practice = [m("pf_pr_up = 0")]
for role, sk in {1: 'cooking', 2: 'melee', 3: 'survival', 4: 'fabrication', 5: 'firstaid'}.items():
    practice.append({"if": {"and": [m(f"u_pf_role == {role}"), m(f"u_skill('{sk}') < 6")]}, "then": [m(f"u_skill('{sk}') += 1"), m("pf_pr_up = 1")]})
practice.append({"if": {"and": [m("pf_pr_up == 1"), m("pf_ch_say")]}, "then": [m("pf_ch_l += 1"), line("practice")]})
files["household.json"] += [
    eoc("PF_HOME_practice", practice, "u = someone who just did their job.  About one chore in eight, they get a little better at it (the job's skill +1, up to 6): cooking, melee, survival, fabrication or first aid."),
    eoc("PF_HOME_burnt", [
        m("pf_burnt_last = time('now')"),
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_bt_cook")},
        m("pf_bt_best = -1"),
        {"u_run_npc_eocs": ["PF_HOME_critic"], "local": True, "npc_range": 20},
        {"if": m("pf_bt_best >= 0"),
         "then": [{"run_eocs": "PF_HOME_burnt_row", "alpha_talker": g("pf_bt_who"), "beta_talker": "u"}],
         "else": [{"if": m("pf_ch_say"), "then": [m("pf_ch_l += 1"), line("burnt_alone")]}]},
        m("pf_burnt_total = value_or(pf_burnt_total, 0) + 1"),
    ], "u = the cook.  The soup burned.  Whoever minds most (hates waste +40, proud +15, plus tension with the cook) says something, and it turns into an argument (concept §2 pillar 5: 'those two argue every single time someone burns the food')."),
    eoc("PF_HOME_critic", [
        {"copy_var": g("pf_bt_cook"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        m("_s = pf_read_x"),
        {"if": {"u_has_trait": "PF_Q_HATES_WASTE"}, "then": [m("_s += 40")]},
        {"if": {"u_has_trait": "PF_Q_PROUD"}, "then": [m("_s += 15")]},
        {"if": {"and": [m("_s >= 15"), m("_s > pf_bt_best")]}, "then": [m("pf_bt_best = _s"), {"u_set_talker": g("pf_bt_who")}]},
    ], condition={"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_bt_cook")]}}]}),
    eoc("PF_HOME_burnt_row", [
        name_into("pf_say_a"), name_into("pf_say_b", "<npc_name>"),
        {"if": m("pf_ch_say"), "then": [m("pf_ch_l += 1"), line("burnt_row")]},
        m("pf_m_str_in = 40"), {"run_eocs": "PF_MK_argument"},
    ], "Alpha = the critic, beta = the cook."),
    eoc("PF_HOME_stay_tick", [
        {"u_run_npc_eocs": ["PF_HOME_stay_check"], "local": True, "npc_range": 60},
    ], "Once a day: anyone who lives with you and has soured on you (tension 60+, or warmth below 10 with no partner, children or household of their own here) packs up and goes.  If they're an A-Life person they start a band of their own out there; otherwise they just walk away.",
        recurrence="1 days", **{"global": True}, condition=m(AT_HOME)),
    # full run day 113: Lisandra Riley joined with her family on day 108 (the family asked; she'd met Dante twice), still had
    # warmth 7 toward him two days later, and walked out alone, pregnant, leaving her partner Hubert and both her children.
    # Not warming to you isn't souring: someone with a partner, children or their own household here stays unless there's
    # real bad blood (tension 60+).
    eoc("PF_HOME_stay_check", [
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        {"if": {"or": [m("pf_read_w < 10"), m("pf_read_x >= 60")]}, "then": [
            m("pf_st_x = pf_read_x"), m("pf_st_ties = 0"), {"u_set_talker": g("pf_st_who")},
            {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_st_uid")},
            {"set_string_var": "none", "target_var": g("pf_st_sweet")},
            {"if": m("value_or(u_pf_has_sweet, 0) == 1"), "then": [{"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_st_sweet")}]},
            m("pf_st_hh = value_or(u_pf_household, 0)"),
            {"u_run_npc_eocs": [{"id": "PF_HOME_stay_tie", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_st_uid")]}}]},
                                 "effect": [
                {"if": {"compare_string": [{"u_val": "pf_uid"}, g("pf_st_sweet")]}, "then": [m("pf_st_ties += 1")]},
                {"if": m("(pf_st_hh > 0) * (value_or(u_pf_household, 0) == pf_st_hh)"), "then": [m("pf_st_ties += 1")]},
                {"if": {"or": [{"compare_string": [{"u_val": "pf_mom"}, g("pf_st_uid")]}, {"compare_string": [{"u_val": "pf_dad"}, g("pf_st_uid")]},
                               {"compare_string": [{"u_val": "pf_guardian"}, g("pf_st_uid")]}]}, "then": [m("pf_st_ties += 1")]}]}],
             "local": True, "npc_range": 60},
            {"if": {"or": [m("pf_st_x >= 60"), m("pf_st_ties == 0")]}, "then": [{"run_eocs": "PF_HOME_leave", "alpha_talker": g("pf_st_who")}]}]},
    ], condition={"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), m("time_since(value_or(u_pf_resident_since, 0)) >= time('2 d')")]}),
    eoc("PF_HOME_leave", [
        name_into("pf_say_a"), line("leaves"),
        m("u_pf_resident = 0"), m("u_pf_role = 0"), m("pf_residents_n = max(value_or(pf_residents_n, 1) - 1, 0)"),
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, m("pf_mv_role = 2"), m("pf_m_str_in = 60"), {"run_eocs": "PF_MV_breakup"},
        {"if": {"u_has_trait": "PF_AGENT"},
         "then": [{"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_band_new_leader")},
                  {"run_eocs": "PF_ALIFE_register_band"},
                  m("pf_ws_task = 1"), m("pf_ws_kind = 0"), {"run_eocs": "PF_WORLD_init_leader"},
                  m("pf_residents_left_total = value_or(pf_residents_left_total, 0) + 1")],
         "else": [{"u_location_variable": {"u_val": "pf_walk_to"}},
                  {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("(rand(1) * 2 - 1) * 50"), "y_adjust": m("rand(40) - 20")},
                  {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]},
    ], "u = someone leaving home.  It lands like a breakup (one-sided, their side).  An A-Life person becomes the leader of a new one-person band (back in the roster, walking off to hunt); anyone else walks away."),
]

files["world.json"] += [
    eoc("PF_WORLD_visit_tick", [
        m("pf_vi_day = floor(time('now') / time('1 d'))"),
        m("pf_vi_best = 999999"), m("pf_wi = 0"),
        {"run_eocs": "PF_WORLD_visit_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
        {"if": m("pf_vi_best < 999999"), "then": [by_uid(["PF_WORLD_visit_go"], g("pf_vi_lead"))]},
    ], "Checked hourly, acts once a day between 14:00 and 15:00: if you have a home, the nearest settled family within about a day's walk (1000 tiles) that hasn't visited in 5 days comes over (one day in three).  Its two waypoints become your home, so A-Life walks it there and it stays; the next morning it goes home.  Off-screen it's data; it walks into the bubble like any band, and if it arrives in time it joins the evening.",
        recurrence="1 hours", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_alife_on, 1) == 1"), m("time_since('midnight', 'unit': 'hours') >= 14"), m("time_since('midnight', 'unit': 'hours') < 15"),
                           m("value_or(pf_vi_day, -1) != floor(time('now') / time('1 d'))"), m("rand(2) == 0")]}),
    eoc("PF_WORLD_visit_i", [
        {"set_string_var": "pf_slot_<global_val:pf_wi>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [by_uid(["PF_WORLD_visit_cand"], {"var_val": "ref"})]},
        m("pf_wi += 1"),
    ]),
    eoc("PF_WORLD_visit_cand", [
        m("_d = distance(u_pf_vpos, pf_home_loc)"),
        {"if": {"and": [m("_d <= 1000"), m("_d > 30"), m("_d < pf_vi_best")]}, "then": [m("pf_vi_best = _d"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_vi_lead")}]},
    ], condition={"and": [m("value_or(u_pf_settled, 0) == 1"), m("value_or(u_pf_visiting, 0) == 0"), m("has_var(u_pf_home)"),
                          {"or": [m("value_or(pf_vi_force, 0) == 1"), cooldown_ok_c("u_pf_visit_last", "5 d")]}]}),
    eoc("PF_WORLD_visit_go", [
        m("u_pf_visiting = 1"), m("u_pf_visit_last = time('now')"), m("u_pf_greeted = 0"), m("u_pf_visits_n = value_or(u_pf_visits_n, 0) + 1"),
        {"copy_var": g("pf_home_loc"), "target_var": {"u_val": "pf_wp_a"}},
        {"location_variable_adjust": {"u_val": "pf_wp_a"}, "x_adjust": 6, "y_adjust": 4},
        {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_wp_b"}},
        {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_goal"}},
        m("pf_visits_total = value_or(pf_visits_total, 0) + 1"),
    ], "u = a settled family's leader: heading to your home for the evening."),
    eoc("PF_WORLD_visit_end_tick", [
        m("pf_wi = 0"),
        {"run_eocs": "PF_WORLD_visit_end_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
    ], "Every morning between 08:00 and 09:00: visiting families head home.", recurrence="1 hours", **{"global": True},
        condition={"and": [m("value_or(pf_visits_total, 0) > 0"), m("time_since('midnight', 'unit': 'hours') >= 8"), m("time_since('midnight', 'unit': 'hours') < 9")]}),
    eoc("PF_WORLD_visit_end_i", [
        {"set_string_var": "pf_slot_<global_val:pf_wi>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [by_uid([{"id": "PF_WORLD_visit_end_one",
            "condition": m("value_or(u_pf_visiting, 0) == 1"),
            "effect": [m("u_pf_visiting = 0"),
                       {"copy_var": {"u_val": "pf_home"}, "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": {"u_val": "pf_home"}, "target_var": {"u_val": "pf_wp_b"}},
                       {"copy_var": {"u_val": "pf_home"}, "target_var": {"u_val": "pf_goal"}}]}], {"var_val": "ref"})]},
        m("pf_wi += 1"),
    ]),
    eoc("PF_WORLD_greet_tick", [
        {"u_location_variable": g("pf_player_pos")},
        m("pf_wi = 0"),
        {"run_eocs": "PF_WORLD_greet_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
    ], "Every 20 minutes while you're awake (playtest 3: a band stopped by and shared food while you slept): a visiting family that has reached your home (within 25 tiles, on-screen) is greeted: they brought food, and everyone there shares a meal with them.  And if you walk up to a settled family's own place, they ask you in (once a day).",
        recurrence="20 minutes", **{"global": True}, condition={"and": [m("value_or(pf_band_n, 0) > 0"), {"not": {"u_has_effect": "sleep"}}]}),
    eoc("PF_WORLD_greet_i", [
        {"set_string_var": "pf_slot_<global_val:pf_wi>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [by_uid(["PF_WORLD_greet_one", "PF_WORLD_host_you", "PF_WORLD_pass_by"], {"var_val": "ref"})]},
        m("pf_wi += 1"),
    ]),
    eoc("PF_WORLD_greet_one", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_home_loc) <= 25"), "then": [
            m("u_pf_greeted = 1"),
            name_into("pf_say_a"),
            {"map_spawn_item": "pemmican", "loc": g("pf_stores_loc"), "count": 3},
            {"if": m(CALM_LINES), "then": [line("visit")]},
            m("pf_m_str_in = 40"), {"u_set_talker": g("pf_vi_guest")}, {"u_run_npc_eocs": ["PF_WORLD_greet_host"], "local": True, "npc_range": 25},
            {"run_eocs": "PF_MK_meal_shared", "beta_talker": "avatar"}]},
    ], "u = a visiting family's leader (on-screen).  Only between 07:00 and 22:00: a family that arrives in the night waits for morning (playtest 3 had them knocking at 02:40).", condition={"and": [m("value_or(u_pf_visiting, 0) == 1"), m("value_or(u_pf_greeted, 0) == 0"),
                                                                  m("value_or(u_pf_online, 0) == 1"),
                                                                  m("time_since('midnight', 'unit': 'hours') >= 7"), m("time_since('midnight', 'unit': 'hours') < 22")]}),
    eoc("PF_WORLD_host_you", [
        m("u_pf_hosted_day = floor(time('now') / time('1 d'))"), m("u_pf_hosted_n = value_or(u_pf_hosted_n, 0) + 1"),
        name_into("pf_say_a"),
        {"u_location_variable": g("pf_vi_av_at")},
        {"run_eocs": {"id": "PF_WORLD_host_food", "effect": [{"u_location_variable": g("pf_vi_av_at")}]}, "alpha_talker": "avatar"},
        {"run_eocs": "PF_GIVE_soup_meat", "alpha_talker": "avatar"},
        {"if": m(CALM_LINES), "then": [line("hosted")]},
        m("pf_m_str_in = 45"), {"run_eocs": "PF_MK_meal_shared", "beta_talker": "avatar"},
        m("pf_hosted_total = value_or(pf_hosted_total, 0) + 1"),
    ], "u = a settled family's leader, at home, with you within 12 tiles of their place: they ask you in and feed you (once a day).  The other half of being neighbors.",
        condition={"and": [m("value_or(u_pf_settled, 0) == 1"), m("value_or(u_pf_visiting, 0) == 0"), m("value_or(u_pf_online, 0) == 1"),
                           m("has_var(u_pf_home)"), m("distance(pf_player_pos, u_pf_home) <= 12"),
                           {"or": [m("value_or(pf_home_set, 0) == 0"), m("distance(u_pf_home, pf_home_loc) > 30")]},
                           m("value_or(u_pf_hosted_day, -1) != floor(time('now') / time('1 d'))")]}),
    # playtest 3 (a fresh world): a band walked into your shelter, fought beside you, and left without ever meeting you.
    # A lone start had no way in.  Now a band on the move that comes near you stops: food, the road, names.
    eoc("PF_WORLD_pass_by", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_player_pos) <= 20"), "then": [{"run_eocs": "PF_WORLD_pass_stop"}]},
    ], "u = the leader of a band on the move (on-screen): do they stop for you?",
        # full run day 113: Lisandra joined Kinfold on day 108 but kept her band-leader flag, and five days later "Lisandra
        # Riley's band again.  This time they sit down for a while…" at her own home.  People who live with you don't pass by.
        condition={"and": [m("value_or(u_pf_is_leader, 0) == 1"), m("value_or(u_pf_settled, 0) == 0"), m("value_or(u_pf_visiting, 0) == 0"),
                           m("value_or(u_pf_resident, 0) == 0"),
                           m("value_or(u_pf_online, 0) == 1"), m(f"value_or(u_pf_pass_day, -1) != {TODAY}"),
                           m("time_since('midnight', 'unit': 'hours') >= 7"), m("time_since('midnight', 'unit': 'hours') < 20"),
                           # day 150: deer, geese and lemmings around a band in the open counted as "monsters near" and the
                           # pass-by never fired; only hostiles matter
                           m("u_monsters_nearby('radius': 8, 'attitude': 'hostile') == 0")]}),
    eoc("PF_WORLD_pass_stop", [
        m(f"u_pf_pass_day = {TODAY}"), m("u_pf_passes_n = value_or(u_pf_passes_n, 0) + 1"),
        name_into("pf_say_a"),
        {"if": m(CALM_LINES), "then": [{"if": m("u_pf_passes_n == 1"), "then": [line("pass_by_first")], "else": [line("pass_by_again")]}]},
        m("pf_pass_first = u_pf_passes_n == 1"),
        # the first meeting is a memory (strength 60, brought up at a fire one day); the meals after it just warm (45, under the recall bar of 50)
        m("pf_m_str_in = pf_pass_first ? 60 : 45"), {"run_eocs": "PF_MK_meal_shared", "beta_talker": "avatar"}] + [
        {"if": {"not": {"compare_string": [{"u_val": f"pf_member_{k}"}, "none"]}}, "then": [by_uid([{"id": f"PF_WORLD_pass_member_{k}",
            "condition": m("value_or(u_pf_online, 0) == 1"),
            "effect": [m("pf_m_str_in = pf_pass_first ? 55 : 45"), {"run_eocs": "PF_MK_meal_shared", "beta_talker": "avatar"}]}], {"u_val": f"pf_member_{k}"})]}
        for k in range(5)] + [
        m("pf_passes_total = value_or(pf_passes_total, 0) + 1"),
    ], "u = the leader of a band on the move (on-screen).  Once a day, by day, when they come within 20 tiles of you and nothing hostile is near them: they stop, share what food they have, ask about the road.  A meal_shared moment between you and each of them, so passing bands can become people you know, and in time people who'll move in."),

    eoc("PF_WORLD_greet_host", [{"run_eocs": "PF_MK_meal_shared", "beta_talker": g("pf_vi_guest")}],
        "u = someone who lives with you: shares a meal with the guest (meal_shared moment).",
        condition=m("value_or(u_pf_resident, 0) == 1")),
]

# ============================================================ THE HORN (first seed; playtest 2026-10-11: nobody defended anyone)
# Your people: they live with you, or they think well enough of you (warmth 20+).  Playtest 3: a stranger in the evac
# shelter raised the camp alarm the first night, because anyone with a People First id counted.
OURS = {"or": [m("value_or(u_pf_resident, 0) == 1"), m("value_or(u_pf_v_AVATAR_w, 0) >= 20")]}
files["horn.json"] = [
    # ---------------------------------------------------------------- alarm (scan, spot, wake, scramble)
    eoc("PF_HORN_tick", [
        {"run_eocs": "PF_THREAT_scan"},
        {"if": {"or": [m("pf_threat > 0"), WATCH_RECENT]},
         "then": [{"if": m("value_or(pf_horn_active, 0) == 0"), "then": [{"run_eocs": "PF_HORN_alarm"}],
                   "else": [{"run_eocs": "PF_HORN_scramble"}]}],
         "else": [{"if": {"and": [m("value_or(pf_horn_active, 0) == 1"), m("time('now') - max(pf_horn_t, value_or(pf_horn_last, 0)) >= time('6 m')")]}, "then": [{"run_eocs": "PF_HORN_allclear"}]}]},
    ], "Every 2 minutes, when there are people around you: if something hostile is close (PF_THREAT_scan), the camp is alarmed; while it lasts, everyone keeps to their job (defenders re-aim at the threat as it moves, children stay away); once it has been calm for a few minutes, the all-clear.",
        recurrence="2 minutes", **{"global": True}, condition=m("value_or(pf_horn_on, 1) == 1")),
    eoc("PF_HORN_alarm", [
        m("pf_horn_active = 1"), m("pf_horn_t = time('now')"), m("pf_hn_escd = 0"),
        m("pf_horn_deaths0 = value_or(pf_ours_dead_total, 0)"),
        {"run_eocs": "PF_HORN_locate"},
        {"if": m("pf_hn_found == 0"), "then": [m("pf_horn_active = 0")], "else": [
            m("pf_hn_people = 0"),
            {"u_run_npc_eocs": ["PF_HORN_count"], "local": True, "npc_range": 30},
            {"if": m("pf_hn_people == 0"), "then": [m("pf_horn_active = 0")], "else": [
                {"set_string_var": "", "target_var": g("pf_hn_spot")},
                {"if": WATCH_RECENT, "then": [{"copy_var": g("pf_wt_spot"), "target_var": g("pf_hn_spot")}]},
                {"if": {"and": [m("value_or(pf_watch_active, 0) == 1"), {"compare_string": [g("pf_hn_spot"), ""]}]}, "then": [
                    {"set_string_var": "pf_name_<global_val:pf_watch_uid>", "target_var": ctx("wn"), "parse_tags": True},
                    {"copy_var": {"var_val": "wn"}, "target_var": g("pf_hn_spot")}]},
                {"if": {"compare_string": [g("pf_hn_spot"), ""]}, "then": [
                    m("pf_hn_best = 9999"), {"u_run_npc_eocs": ["PF_HORN_spotter"], "local": True, "npc_range": 30}]},
                # full run: six alarms in three hours, three lines each (alarm, a child carried off, all-clear), for dead drifting
                # past the windows.  A new alarm within 30 minutes of the last all-clear is a quiet one: people still move, no lines.
                # full run day 77: nine alarms in eleven hours, about one an hour, so the 30-minute window never caught any; an
                # alarm is also quiet within 3 hours of the last one that was told (people still move; the log stays readable)
                m("pf_hn_quiet = (time('now') - value_or(pf_horn_clear_t, -999999) < time('30 m')) + (time('now') - value_or(pf_horn_said_t, -999999) < time('3 h')) > 0"),
                {"if": {"and": [{"not": {"compare_string": [g("pf_hn_spot"), ""]}}, m("pf_hn_quiet == 0")]}, "then": [
                    m("pf_horn_said_t = time('now')"),
                    # playtest 3: three alarms in an afternoon, word for word the same
                    m("_v = rand(3)"), {"if": m("_v == value_or(pf_hn_last, -1)"), "then": [m("_v = (_v + 1) % 4")]}, m("pf_hn_last = _v"),
                    {"if": m("_v == 0"), "then": [line("horn_alarm")]}, {"if": m("_v == 1"), "then": [line("horn_alarm_1")]},
                    {"if": m("_v == 2"), "then": [line("horn_alarm_2")]}, {"if": m("_v == 3"), "then": [line("horn_alarm_3")]}]},
                # full run: woken one to three times a night for dead seen through the windows that the guard handled outside;
                # only shake you awake when something is close to you (6 tiles); the alarm and all-clear still go to the log
                # day 77: still woken twice in an hour for dead behind the shelter wall (monsters_nearby ignores walls), so the
                # nearest threat must also be in plain sight of you
                {"if": {"and": [{"u_has_effect": "sleep"}, m("u_monsters_nearby('radius': 6) > 0"), m("distance(pf_hn_av, pf_hn_att) <= 6"),
                                {"line_of_sight": 6, "loc_1": g("pf_hn_av"), "loc_2": g("pf_hn_att")}]},
                 "then": [{"u_lose_effect": "sleep"}, {"u_lose_effect": "lying_down"}, {"u_lose_effect": "PF_sleep_easy"}, line("horn_wake_you")]},
                m("pf_horn_new = 1"),
                {"run_eocs": "PF_HORN_scramble"},
                m("pf_horn_new = 0"),
                m("pf_horn_alarms_total = value_or(pf_horn_alarms_total, 0) + 1")]}]},
    ], "u = avatar, a new threat.  The watcher (if someone has the watch) or the nearest awake adult raises the alarm; you're shaken awake if you were asleep; then the scramble."),
    eoc("PF_HORN_count", [m("pf_hn_people += 1")], condition={"and": [m("has_var(u_pf_uid)"), m("u_val('age') >= 2"), OURS]}),
    # full run day 99: "3 of yours didn't live to see it" with four dead; pf_deaths_total only counts A-Life agents, and Evan (the
    # first companion) wasn't one.  Any of ours who dies counts here (not visitors who leave: envoys, lifespan NPCs).
    eoc("PF_OURS_died", [m("pf_ours_dead_total = value_or(pf_ours_dead_total, 0) + 1"),
        # for the children's next days (gen_family PF_FAM_kid_loss): who, and whether it was more than one
        m("pf_loss_multi = (time('now') - value_or(pf_loss_t, -999999) < time('12 h')) ? 1 : 0"),
        m("pf_loss_n = value_or(pf_loss_n, 0) + 1"), m("pf_loss_t = time('now')"),
        {"set_string_var": "<u_name>", "target_var": g("pf_loss_name"), "parse_tags": True},
        # v0.8 housekeeping: a resident's things are gathered up a couple of hours later (PF_HOUSE_estate_tick)
        {"if": m("value_or(u_pf_resident, 0) == 1"), "then": [
            m("pf_est_pending = 1"), m("pf_est_t = time('now')"), {"u_location_variable": g("pf_est_at")},
            {"set_string_var": "<u_name>", "target_var": g("pf_est_name"), "parse_tags": True},
            m("pf_est_hascn = has_var(u_pf_corner)"),
            {"if": m("pf_est_hascn == 1"), "then": [{"copy_var": {"u_val": "pf_corner"}, "target_var": g("pf_est_cn")}]}]}],
        "Signal: one of ours dies (resident, or someone who cares for you).",
        condition={"and": ["has_alpha", "u_is_npc", m("has_var(u_pf_uid)"), OURS, m("value_or(u_pf_envoy, 0) == 0"), m("value_or(u_pf_nv_gone, 0) == 0")]},
        eoc_type="EVENT", required_event="character_dies"),
    # full run day 123: Lisandra, Easter and the baby died in a fight a few tiles from Dante's bed, and he slept through it (the
    # Horn only wakes you for a threat in sight within 6 tiles).  When one of ours is hit near you while you sleep, someone wakes you.
    eoc("PF_WAKE_on_hurt", [
        {"u_location_variable": g("pf_wk_at")},
        {"run_eocs": {"id": "PF_WAKE_on_hurt_av", "effect": [
            {"u_location_variable": g("pf_wk_av")},
            {"if": {"and": [{"u_has_effect": "sleep"}, m("distance(pf_wk_av, pf_wk_at) <= 20"),
                            m("time('now') - value_or(pf_wk_t, -999999) >= time('10 m')")]}, "then": [
                m("pf_wk_t = time('now')"),
                {"u_lose_effect": "sleep"}, {"u_lose_effect": "lying_down"}, {"u_lose_effect": "PF_sleep_easy"},
                name_into("pf_say_a"), line("hurt_wake_you")]}]}, "alpha_talker": "avatar"},
    ], "Signal: one of ours is hit by a monster within 20 tiles of you while you sleep: you're shaken awake (once every 10 minutes).",
        condition={"and": ["has_alpha", "has_beta", "u_is_npc", "npc_is_monster", m("has_var(u_pf_uid)"), OURS]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    eoc("PF_HORN_locate", [
        m("pf_hn_found = 0"), m("pf_hn_dmin = 9999"), {"u_location_variable": g("pf_hn_av")},
        {"u_run_monster_eocs": ["PF_HORN_mon"], "monster_range": 25},
        {"if": {"and": [m("pf_hn_found == 0"), m("value_or(pf_hn_hurt_t, -1) >= time('now') - time('1 m')")]},
         "then": [{"copy_var": g("pf_hn_hurt_mpos"), "target_var": g("pf_hn_att")}, m("pf_hn_found = 1")]},
        {"if": {"and": [m("pf_hn_found == 0"), WATCH_RECENT]}, "then": [{"copy_var": g("pf_wt_seen_mpos"), "target_var": g("pf_hn_att")}, m("pf_hn_found = 1")]},
    ], "u = avatar.  pf_hn_att = the nearest hostile monster within 25 tiles of you, or else whatever just hurt one of ours (it can be out of your sight: playtest 2), or else what the town watch saw (Town pass 3)."),
    eoc("PF_HORN_mon", [
        {"u_location_variable": g("pf_hn_mpos")},
        {"if": m("distance(pf_hn_mpos, pf_hn_av) < pf_hn_dmin"), "then": [m("pf_hn_dmin = distance(pf_hn_mpos, pf_hn_av)"), m("pf_hn_found = 1"),
                                                                       {"copy_var": g("pf_hn_mpos"), "target_var": g("pf_hn_att")}]},
    ], condition=m("u_monsters_nearby('radius': 0) > 0")),
    eoc("PF_HORN_spotter", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_hn_att) < pf_hn_best"), "then": [m("pf_hn_best = distance(u_pf_pos, pf_hn_att)"), name_into("pf_hn_spot")]},
    ], condition={"and": [ADULT, {"not": {"u_has_effect": "sleep"}}, m("has_var(u_pf_uid)"), OURS]}),
    eoc("PF_HORN_scramble", [
        {"run_eocs": "PF_HORN_locate"},
        {"if": m("pf_hn_found == 1"), "then": [
            m("pf_hn_esc_n = 0"),
            {"u_run_npc_eocs": ["PF_HORN_child"], "local": True, "npc_range": 30},
            m("pf_hn_n = 0"), m("pf_hn_esc_said = 0"),
            {"u_run_npc_eocs": ["PF_HORN_adult"], "local": True, "npc_range": 30}]},
    ], "u = avatar.  Children first (each one runs to safety and names who should go with them), then the adults (a child's parent or guardian goes with them; everyone else runs at the threat)."),
    eoc("PF_HORN_child", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"run_eocs": "PF_HORN_safe_spot"},
        {"copy_var": g("pf_hn_safe"), "target_var": {"u_val": "pf_walk_to"}},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
        {"set_string_var": "none", "target_var": g("pf_hn_esc")},
        {"copy_var": {"u_val": "pf_dad"}, "target_var": g("pf_hn_esc")},
        {"if": {"not": {"compare_string": [{"u_val": "pf_mom"}, "none"]}}, "then": [{"copy_var": {"u_val": "pf_mom"}, "target_var": g("pf_hn_esc")}]},
        {"if": {"not": {"compare_string": [{"u_val": "pf_guardian"}, "none"]}}, "then": [{"copy_var": {"u_val": "pf_guardian"}, "target_var": g("pf_hn_esc")}]},
        {"if": {"and": [m("pf_hn_esc_n < 6"), {"not": {"compare_string": [g("pf_hn_esc"), "none"]}}]}, "then": [
            {"set_string_var": "pf_hn_esc_<global_val:pf_hn_esc_n>", "target_var": ctx("er"), "parse_tags": True},
            {"copy_var": g("pf_hn_esc"), "target_var": {"var_val": "er"}},
            {"set_string_var": "pf_hn_kid_<global_val:pf_hn_esc_n>", "target_var": ctx("ek"), "parse_tags": True},
            {"set_string_var": "<u_name>", "target_var": {"var_val": "ek"}, "parse_tags": True},
            m("pf_hn_esc_n += 1")]},
        m("u_pf_fright_t = time('now')"),
    ], "u = a child (walking; babies are carried, so they go wherever their carrier goes).  Runs to the safe spot (and it frightened them: Reckoning nightmares).",
        condition={"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}, OURS]}),
    eoc("PF_HORN_safe_spot", [
        {"if": {"and": [m("value_or(pf_home_set, 0) == 1"), m("distance(pf_home_loc, pf_hn_att) > 15"), m("distance(pf_home_loc, u_pf_pos) < 40")]},
         "then": [{"copy_var": g("pf_home_loc"), "target_var": g("pf_hn_safe")}],
         "else": [{"copy_var": {"u_val": "pf_pos"}, "target_var": g("pf_hn_safe")},
                  {"location_variable_adjust": g("pf_hn_safe"),
                   "x_adjust": m("((u_pf_pos.x > pf_hn_att.x) - (u_pf_pos.x < pf_hn_att.x)) * 12"),
                   "y_adjust": m("((u_pf_pos.y > pf_hn_att.y) - (u_pf_pos.y < pf_hn_att.y)) * 12")}]},
    ], "u = someone getting away from pf_hn_att.  Home, if it's away from the threat and not far; otherwise 12 tiles straight away from it."),
    eoc("PF_HORN_adult", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": {"u_has_effect": "sleep"}, "then": [{"u_lose_effect": "sleep"}, {"u_lose_effect": "lying_down"}]},
        m("pf_hn_escort = -1"),
    ] + [{"if": {"and": [m(f"pf_hn_esc_n > {k}"), {"compare_string": [{"u_val": "pf_uid"}, g(f"pf_hn_esc_{k}")]}]}, "then": [m(f"pf_hn_escort = {k}")]} for k in range(6)] + [
        {"if": m("pf_hn_escort >= 0"),
         "then": [{"run_eocs": "PF_HORN_safe_spot"},
                  {"copy_var": g("pf_hn_safe"), "target_var": {"u_val": "pf_walk_to"}},
                  {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
                  {"if": m("value_or(pf_hn_escd, 0) == 0"), "then": [
                      m("pf_hn_escd = 1"), name_into("pf_hn_escd_a"),
                      {"set_string_var": "pf_hn_kid_<global_val:pf_hn_escort>", "target_var": ctx("ek2"), "parse_tags": True},
                      {"copy_var": {"var_val": "ek2"}, "target_var": g("pf_hn_escd_b")}]},
                  {"if": {"and": [m("pf_hn_esc_said == 0"), m("value_or(pf_horn_new, 0) == 1"), m(CALM_LINES), m("value_or(pf_hn_quiet, 0) == 0")]}, "then": [
                      m("pf_hn_esc_said = 1"), name_into("pf_say_a"),
                      {"set_string_var": "pf_hn_kid_<global_val:pf_hn_escort>", "target_var": ctx("ek"), "parse_tags": True},
                      {"copy_var": {"var_val": "ek"}, "target_var": g("pf_say_b")},
                      m("_p = rand(3)"), {"if": m("_p == value_or(pf_hn_sh_last, -1)"), "then": [m("_p = (_p + 1) % 4")]}, m("pf_hn_sh_last = _p"),
                  ] + [{"if": m(f"_p == {i}"), "then": [line(f"horn_shield{'_' + str(i) if i else ''}")]} for i in range(4)]}],
         # full run day 97: something in the river hurt someone on watch, every adult was sent to its spot, and all eleven people
         # spent the night in the water 30 tiles out.  A threat on water is fought from the bank (vanilla aims at it); no walk order.
         "else": [{"if": {"not": {"map_terrain_with_flag": "SWIMMABLE", "loc": g("pf_hn_att")}}, "then": [
                      {"copy_var": g("pf_hn_att"), "target_var": {"u_val": "pf_walk_to"}},
                      {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]},
                  m("pf_hn_n += 1"), {"if": m("pf_hn_n == 1"), "then": [name_into("pf_hn_first")]},
                  m("u_pf_horn_alarm = pf_horn_t")]},
    ], "u = an adult near the trouble (woken if asleep).  A parent or guardian of a child who is running goes with them; everyone else runs at the threat (vanilla combat takes it from there).",
        # the one who stays in with the children on a siege night (gen_keep PF_SIEGE_wave) isn't sent out
        condition={"and": [ADULT, m("has_var(u_pf_uid)"), OURS,
                           m("(value_or(pf_sg_state, 0) == 1) * (value_or(u_pf_sg_keep_t, -1) == value_or(pf_sg_t0, -2)) == 0")]}),
    # ---------------------------------------------------------------- reckoning (all-clear)
    eoc("PF_HORN_allclear", [
        m("pf_horn_active = 0"),
        m("pf_hn_lost = value_or(pf_ours_dead_total, 0) - value_or(pf_horn_deaths0, 0)"),
        # a loss is always told; a quiet alarm's all-clear isn't
        # full run: "Everyone's still here" between two siege waves, on the day someone died, and minutes before a wounded man died
        m("pf_hn_hurt = 0"),
        {"u_run_npc_eocs": [{"id": "PF_HORN_hurt_count", "condition": {"and": [OURS, {"or": [m("u_hp('torso') <= u_hp_max('torso') * 0.5"), m("u_hp('head') <= u_hp_max('head') * 0.5")] +
            [{"u_has_effect": "bleed", "bodypart": bp} for bp in ["torso", "head", "arm_l", "arm_r", "leg_l", "leg_r"]]}]},
            "effect": [m("pf_hn_hurt += 1"), {"if": m("pf_hn_hurt == 1"), "then": [name_into("pf_hn_hurt_a")]}]}], "local": True, "npc_range": 60},
        {"if": m("pf_hn_lost > 0"), "then": [line("horn_clear_loss")],
         "else": [{"if": {"and": [m(CALM_LINES), m("value_or(pf_hn_quiet, 0) == 0")]}, "then": [
             {"if": m("(value_or(pf_sg_state, 0) == 1) * (value_or(pf_sg_wave, 0) > 0)"), "then": [line("horn_lull")],
              "else": [{"if": m("pf_hn_hurt > 0"), "then": [line("horn_clear_hurt")],
                        "else": [{"if": m("time('now') - value_or(pf_loss_t, -999999) < time('12 h')"), "then": [line("horn_clear_grief")],
                                  "else": [line("horn_clear")]}]}]}]}]},
        m("pf_horn_clear_t = time('now')"),
        # full run: "won't let go … for the rest of the day" twice in two hours (three alarms that afternoon); once a day
        {"if": {"and": [m("value_or(pf_hn_escd, 0) == 1"), m("pf_hn_lost == 0"), m(f"value_or(pf_cling_day, -1) != {TODAY}")]}, "then": [
            m(f"pf_cling_day = {TODAY}"),
            {"copy_var": g("pf_hn_escd_a"), "target_var": g("pf_say_a")}, {"copy_var": g("pf_hn_escd_b"), "target_var": g("pf_say_b")},
            # day 81: "for the rest of the day" at two in the morning
            {"if": {"and": [m("time_since('midnight', 'unit': 'hours') >= 5"), m("time_since('midnight', 'unit': 'hours') < 20")]},
             "then": [{"set_string_var": "day", "target_var": g("pf_rk_part")}], "else": [{"set_string_var": "night", "target_var": g("pf_rk_part")}]},
            line("rk_clings")]},
        m("pf_hn_escd = 0"),
        m("pf_hn_esc_n = 0"),
        m("pf_hn_n = 0"),
        {"u_run_npc_eocs": ["PF_HORN_stand_down"], "local": True, "npc_range": 60},
    ], "u = avatar, a few minutes after the last threat.  Everyone stands down (walk orders dropped); those who were there share the danger with you (shared_danger moment); a head count, with a different line if someone didn't make it."),
    eoc("PF_HORN_stand_down", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"u_set_guard_pos": {"u_val": "pf_pos"}},
        # day 97: standing down where they stood left the household in the river all night; people who live here go home
        {"if": m("value_or(u_pf_resident, 0) == 1"), "then": [{"run_eocs": "PF_HOME_walk_home"}]},
        {"if": {"and": [ADULT, m("value_or(u_pf_horn_alarm, -1) == pf_horn_t")]}, "then": [
            m("pf_m_str_in = 45"), {"run_eocs": "PF_MK_shared_danger", "beta_talker": "avatar"}]},
    ], condition=m("has_var(u_pf_uid)")),
    # ---------------------------------------------------------------- hurt (one of ours is attacked: immediate, before the next scan)
    eoc("PF_HORN_hurt", [
        m("u_pf_horn_t = time('now')"),
        {"npc_location_variable": g("pf_hn_hurt_mpos")}, m("pf_hn_hurt_t = time('now')"), m("pf_horn_last = time('now')"),
        {"run_eocs": "PF_HORN_hurt_now", "alpha_talker": "avatar"},
    ], "Signal: one of ours is hurt by a monster.  Don't wait for the 2-minute scan: alarm now (or, if already alarmed, scramble again).  Vanilla neutral NPCs only fight for themselves; the playtest had a zombie kill Rhonda and a child while adults stood a few tiles away.",
        condition={"and": ["has_alpha", "has_beta", "u_is_npc", "npc_is_monster", m("has_var(u_pf_uid)"), m("value_or(pf_horn_on, 1) == 1"),
                           cooldown_ok_c("u_pf_horn_t", "1 m")]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    eoc("PF_HORN_hurt_now", [
        {"if": m("value_or(pf_horn_active, 0) == 0"), "then": [{"run_eocs": "PF_HORN_alarm"}], "else": [{"run_eocs": "PF_HORN_scramble"}]},
    ], "u = avatar."),
    # ---------------------------------------------------------------- a band's own cry for help
    # full run (day 62): a beaver hidden in the river (WATER_CAMOUFLAGE: "Something misses Bernard Leggett!") killed a band's
    # child over an hour while two adults of the band talked a few tiles away.  Nobody could see the attacker, so the engine's
    # defense (patch 6) never fired, and the child dodged in place instead of running.  The Horn only raises your people.
    # Now a hurt band member cries out: the band's adults within 30 tiles come to them (holding the band's walk, as a wave
    # does), and a hurt child runs to the nearest of them.  Up close the adults can see the thing and fight it.
    eoc("PF_BAND_hurt", [
        m("u_pf_bh_t = time('now')"), m("pf_bh_band = u_pf_band"), m("pf_bh_kid = 0"), m("pf_bh_n = 0"), m("pf_bh_best = 999"),
        {"if": {"u_has_trait": "PF_CHILD"}, "then": [m("pf_bh_kid = 1")]},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_bh_uid")},
        {"u_location_variable": g("pf_bh_pos")}, name_into("pf_bh_who"),
        {"u_run_npc_eocs": ["PF_BAND_hurt_come"], "local": True, "npc_range": 30},
        {"if": m("pf_bh_n > 0"), "then": [
            {"if": m("pf_bh_kid == 1"), "then": [
                m("u_pf_wave_until = time('now') + time('10 m')"),
                {"copy_var": g("pf_bh_safe"), "target_var": {"u_val": "pf_walk_to"}}, {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]},
            m("pf_band_cries_total = value_or(pf_band_cries_total, 0) + 1"),
            {"run_eocs": "PF_BAND_hurt_say", "alpha_talker": "avatar"}],
         "else": [{"if": m("pf_bh_kid == 1"), "then": [{"run_eocs": "PF_HURT_away_do"}]}]},
    ], "Signal: a band member is hurt by a monster.  Their band's adults come; a child runs to the nearest one.",
        # full run day 85: band ids come from roster slots, which are reused; a new band took Mariano's old slot (id), and when
        # one of them was hurt in the river, Mariano (a resident still carrying that id) waded 63 tiles out to them.
        # Residents neither cry nor answer as a band (the Horn is theirs), and joining clears the id (PF_HOME_join_one).
        condition={"and": ["has_alpha", "has_beta", "u_is_npc", "npc_is_monster", m("has_var(u_pf_uid)"), m("value_or(u_pf_band, 0) > 0"),
                           m("value_or(u_pf_resident, 0) == 0"), cooldown_ok_c("u_pf_bh_t", "1 m")]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    # full run (day 62, again): Shawana stood dodging "Something" (the same hidden beaver) for most of an hour.  NPCs don't react to
    # an attacker they can't see.  Anyone of ours who is hit gets a walk order 6 tiles straight away from the attacker; vanilla
    # combat overrides it while they can see an enemy to fight, so it only matters when they can't.  Band children run to an
    # adult instead (PF_BAND_hurt).
    eoc("PF_HURT_away", [{"run_eocs": "PF_HURT_away_do"}],
        "Signal: one of ours (not a band child: they run to an adult) is hit by a monster.  Step away from it.",
        condition={"and": ["has_alpha", "has_beta", "u_is_npc", "npc_is_monster", m("has_var(u_pf_uid)"), cooldown_ok_c("u_pf_away_t", "30 s"),
                           {"not": {"and": [{"u_has_trait": "PF_CHILD"}, m("value_or(u_pf_band, 0) > 0")]}}]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    eoc("PF_HURT_away_do", [
        m("u_pf_away_t = time('now')"),
        {"u_location_variable": g("pf_ha_me")}, {"npc_location_variable": g("pf_ha_mon")},
        {"copy_var": g("pf_ha_me"), "target_var": {"u_val": "pf_walk_to"}},
        {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": {"math": ["clamp(pf_ha_me.x - pf_ha_mon.x, -1, 1) * 6"]},
         "y_adjust": {"math": ["clamp(pf_ha_me.y - pf_ha_mon.y, -1, 1) * 6"]}},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
    ], "u = the hurt person, n = the monster.  A walk order 6 tiles straight away from it."),
    eoc("PF_BAND_hurt_come", [
        m("u_pf_wave_until = time('now') + time('30 m')"),
        {"copy_var": g("pf_bh_pos"), "target_var": {"u_val": "pf_walk_to"}},
        {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": 1},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
        m("pf_bh_n += 1"),
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_bh_pos) < pf_bh_best"), "then": [
            m("pf_bh_best = distance(u_pf_pos, pf_bh_pos)"), name_into("pf_bh_resc"), {"copy_var": {"u_val": "pf_pos"}, "target_var": g("pf_bh_safe")}]},
    ], "u = an adult of the hurt person's band (not them).  Comes to them; the nearest is the one named.",
        condition={"and": [ADULT, m("value_or(u_pf_band, 0) == pf_bh_band"), m("value_or(u_pf_resident, 0) == 0"),
                           {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_bh_uid")]}}]}),
    eoc("PF_BAND_hurt_say", [
        {"u_location_variable": g("pf_bh_av")},
        {"if": m("distance(pf_bh_av, pf_bh_pos) <= 30"), "then": [
            {"if": m("pf_bh_kid == 1"), "then": [line("band_cry_kid")], "else": [line("band_cry")]}]},
    ], "u = avatar.  Only if you're close enough to hear it (30 tiles)."),
]

# ============================================================ RECKONING (the aftermath: Hearth -> Horn -> Reckoning, concept section 3)
# Pass 1 (2026-10-11): tending the wounded once it's calm, the fight retold at that evening's fire, and children who won't let
# go of their parent after the all-clear.  Rescues themselves are v0.1's (life/combat.json); this adds what comes after.  JSON only: works on the official build too (people only come from far away with
# the engine build, but anyone who happens to be close can still save someone).
RK_PARTS = ["torso", "head", "arm_l", "arm_r", "leg_l", "leg_r"]
STORMY = {"or": [{"is_weather": w} for w in ("early_portal_storm", "distant_portal_storm", "close_portal_storm", "portal_storm", "strong_portal_storm")]}
RK_RECENT = "time('now') - time('1 m')"
_BLEED_PARTS = ["torso", "head", "eyes", "mouth", "arm_l", "arm_r", "hand_l", "hand_r", "leg_l", "leg_r", "foot_l", "foot_r"]
# full run day 153: Fernando Fair joined with wounds from the band's fights a day old, went on bleeding at home, and died in the
# night: tending only looked at people hurt in the last 6 hours.  Anyone actually bleeding (any body part) counts too.
BLEEDING = {"or": [{"u_has_effect": "bleed", "bodypart": bp} for bp in _BLEED_PARTS] + [{"u_has_effect": "bleed"}]}
NEEDS_TENDING = {"and": [{"or": [{"and": [m("value_or(u_pf_hurt_t, -1) > value_or(u_pf_tended_t, -1)"), m("u_pf_hurt_t >= time('now') - time('6 h')"),
                                          m("u_pf_hurt_t < time('now') - time('2 m')")]},
                                 BLEEDING]},
                         m("value_or(u_pf_tended_t, -1) < time('now') - time('30 m')"),
                         # "hostile" in monsters_nearby only means "not a pet": a stray animal, or the dead pressed against the
                         # wall outside, counted.  Something right beside them still stops the tending.
                         m("u_monsters_nearby('radius': 3) == 0")]}
# (playtest 2: a zombie chewed on Jeni out of your sight for an hour; the calm check only looks around you, so Alla
#  "tended" her every few minutes in the middle of it.  Now: no monster within 5 of them, last hit 2+ minutes ago,
#  and once per half hour at most.)
files["reckoning.json"] = [
    {"type": "morale_type", "id": "PF_morale_alive", "text": "Still alive, all of us"},
    eoc("PF_RK_hurt", [m("u_pf_hurt_t = time('now')"), m("u_pf_fright_t = time('now')"), m("pf_rk_need = 1")],
        "Signal: you or one of ours is hurt by a monster.  Stamps the time: v0.1's rescue check counts it, and wounded NPCs get tended (you are tended by v0.1's PF_WOUND_tick).",
        condition={"and": ["has_alpha", "has_beta", "npc_is_monster", {"or": ["u_is_avatar", {"and": ["u_is_npc", m("has_var(u_pf_uid)")]}]}]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    # ---------------------------------------------------------------- rescues are detected by v0.1's PF_COMBAT_kill -> PF_SAVE_record (life/combat.json)
    eoc("PF_RK_note_rescue", [
        {"if": m(f"value_or(pf_rk_day, -1) != {TODAY}"), "then": [m("pf_rk_n_today = 0")]},
        m(f"pf_rk_day = {TODAY}"), m("pf_rk_n_today += 1"), m("pf_rescues_total = value_or(pf_rescues_total, 0) + 1"),
        {"copy_var": g("pf_say_a"), "target_var": g("pf_rk_hero")}, {"copy_var": g("pf_say_b"), "target_var": g("pf_rk_hsaved")},
        m("pf_rk_hero_av = pf_save_case == 2"), m("pf_rk_saved_av = pf_save_case == 1"),
    ], "Called by PF_SAVE_record (pf_say_a = the saver, pf_say_b = the saved, pf_save_case 1 = you were saved, 2 = you saved them, 3 = between NPCs).  Notes today's rescue for the evening retelling."),
    # ---------------------------------------------------------------- tending the wounded (once it's calm)
    eoc("PF_RK_tick", [
        {"run_eocs": "PF_THREAT_scan"},
        {"if": m("pf_threat == 0"), "then": [
            m("pf_rk_need = 0"), m("pf_rk_hn = 0"),
            {"u_run_npc_eocs": ["PF_RK_hurt_one"], "local": True, "npc_range": 30},
        ] + [{"if": m(f"pf_rk_hn > {k}"), "then": [{"run_eocs": "PF_RK_tend", "beta_talker": g(f"pf_rk_h{k}")}]} for k in range(3)] + [
            {"u_location_variable": g("pf_rk_avpos")},
            {"u_run_npc_eocs": ["PF_RK_fled_one"], "local": True, "npc_range": 30}]},
    ], "Every 3 minutes, only after someone was hurt (pf_rk_need): once nothing hostile is around, up to three wounded people are tended by a carer or the nearest adult who isn't hurt themselves.",
        recurrence="3 minutes", **{"global": True}, condition=m("value_or(pf_rk_need, 0) == 1")),
    eoc("PF_RK_sweep", [m("pf_rk_need = 1")],
        "Every 30 minutes: look for anyone still bleeding (old wounds, someone who arrived hurt), not only after a fresh hit.",
        recurrence="30 minutes", **{"global": True}),
    eoc("PF_RK_hurt_one", [
        {"if": m("pf_rk_hn == 0"), "then": [{"u_set_talker": g("pf_rk_h0")}]},
        {"if": m("pf_rk_hn == 1"), "then": [{"u_set_talker": g("pf_rk_h1")}]},
        {"if": m("pf_rk_hn == 2"), "then": [{"u_set_talker": g("pf_rk_h2")}]},
        m("pf_rk_hn += 1"),
    ], condition={"and": [m("has_var(u_pf_uid)"), m("pf_rk_hn < 3"), NEEDS_TENDING]}),
    eoc("PF_RK_tend", [
        {"npc_location_variable": g("pf_rk_hpos")},
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_rk_huid")}, {"npc_set_talker": g("pf_rk_hcur")},
        {"set_string_var": "<npc_name>", "target_var": g("pf_say_b"), "parse_tags": True},
        m("pf_rk_tb = -999"), m("pf_rk_relax = 0"),
        {"u_run_npc_eocs": ["PF_RK_tender_cand"], "local": True, "npc_range": 40},
        # full run day 100: after the siege everyone was hurt, nobody was fit to tend, and Isaias (the carer, bitten pulling
        # people out) died of it the next morning.  If nobody unhurt is near, a hurt adult tends anyway.
        {"if": m("pf_rk_tb == -999"), "then": [m("pf_rk_relax = 1"), {"u_run_npc_eocs": ["PF_RK_tender_cand"], "local": True, "npc_range": 40}]},
        {"if": m("pf_rk_tb > -999"), "then": [
            {"run_eocs": "PF_RK_tend_do", "alpha_talker": g("pf_rk_tender"), "beta_talker": g("pf_rk_hcur")},
            {"if": m(CALM_LINES), "then": [line("rk_tended")]}]},
    ], "u = avatar, n = someone wounded.  Picks who tends them: an awake adult within 20 tiles of them who isn't hurt, preferring the household carer and first aid skill."),
    eoc("PF_RK_tender_cand", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_rk_hpos) <= 20"), "then": [
            m("_s = 100 - distance(u_pf_pos, pf_rk_hpos) * 2 + u_skill('firstaid') * 8 + (value_or(u_pf_role, 0) == 5) * 40 + (value_or(u_pf_role, 0) == 9) * 80"),
            {"if": m("_s > pf_rk_tb"), "then": [m("pf_rk_tb = _s"), {"u_set_talker": g("pf_rk_tender")}, name_into("pf_say_a")]}]},
    ], condition={"and": [ADULT, m("has_var(u_pf_uid)"), {"not": {"u_has_effect": "sleep"}}, {"not": {"u_has_flag": "CANNOT_ATTACK"}},
                          {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_rk_huid")]}},
                          {"or": [m(f"value_or(u_pf_hurt_t, -1) < {RK_RECENT}"), m("value_or(pf_rk_relax, 0) == 1")]}]}),
    eoc("PF_RK_tend_do", [
    ] + [m(f"n_hp('{bp}') = min(n_hp('{bp}') + 8, n_hp_max('{bp}'))") for bp in RK_PARTS] + [
        {"npc_lose_effect": "bleed", "target_part": "ALL"}, {"npc_lose_effect": "bite", "target_part": "ALL"},
        m("n_pf_tended_t = time('now')"),
        {"run_eocs": "PF_MK_care_given"},
        m("pf_tended_total = value_or(pf_tended_total, 0) + 1"),
    ], "u = the one tending, n = the wounded.  Cleans and wraps the wounds: a little hp back on every part, bleeding stopped, bites cleaned (so they don't go bad), and a care_given moment."),
    # ---------------------------------------------------------------- who ran (pf_fled_t is stamped by the engine build, patch 9)
    eoc("PF_RK_fled_one", [
        m("u_pf_fled_seen = u_pf_fled_t"),
        {"u_set_talker": g("pf_rk_fleer")}, name_into("pf_say_a"),
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_rk_fuid")},
        {"u_location_variable": g("pf_rk_fpos")},
        m("pf_rk_vbest = -1"), m("pf_rk_v_av = 0"),
        {"run_eocs": "PF_RK_fled_av", "alpha_talker": "avatar"},
        {"if": m("pf_rk_v_av == 0"), "then": [{"u_run_npc_eocs": ["PF_RK_fled_victim"], "local": True, "npc_range": 30}]},
        {"if": m("pf_rk_v_av == 1"), "then": [
            m("pf_m_str_in = 60"), {"run_eocs": "PF_MK_ran_off", "beta_talker": "avatar"},
            {"if": m(CALM_LINES), "then": [line("rk_ran_you")]}]},
        {"if": {"and": [m("pf_rk_v_av == 0"), m("pf_rk_vbest > 0")]}, "then": [
            {"run_eocs": "PF_MK_ran_off", "beta_talker": g("pf_rk_victim")},
            {"if": {"and": [m(CALM_LINES), m("distance(pf_rk_avpos, pf_rk_fpos) <= 30")]}, "then": [line("rk_ran")]}]},
        {"if": m("pf_rk_v_av + (pf_rk_vbest > 0) > 0"), "then": [m("pf_ran_total = value_or(pf_ran_total, 0) + 1")]},
    ], "u = an adult who broke and ran in the last 15 minutes (engine stamp pf_fled_t), and isn't badly hurt themselves (torso and head at 50% or more: running wounded is sensible).  If you or one of ours was hurt nearby, the one they left behind (you first, else the most recently hurt) gets a ran_off moment: they trust the runner less, and so does everyone who saw it.  Running when nobody got hurt costs nothing.",
        condition={"and": [ADULT, m("has_var(u_pf_uid)"), {"not": {"u_has_flag": "CANNOT_ATTACK"}},
                           m("value_or(u_pf_fled_t, -1) >= time('now') - time('15 m')"), m("value_or(u_pf_fled_seen, -1) < u_pf_fled_t"),
                           m("min(u_hp('torso') / max(1, u_hp_max('torso')), u_hp('head') / max(1, u_hp_max('head'))) >= 0.5")]}),
    eoc("PF_RK_fled_av", [
        {"if": {"and": [m("distance(pf_rk_avpos, pf_rk_fpos) <= 30"), m("value_or(u_pf_hurt_t, -1) >= time('now') - time('15 m')")]},
         "then": [m("pf_rk_v_av = 1"), m("pf_rk_vbest = u_pf_hurt_t")]},
    ], "u = avatar.  Were you the one left behind?"),
    eoc("PF_RK_fled_victim", [
        m("pf_rk_vbest = u_pf_hurt_t"), {"u_set_talker": g("pf_rk_victim")}, name_into("pf_say_b"),
    ], condition={"and": [m("has_var(u_pf_uid)"), {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_rk_fuid")]}},
                          m("value_or(u_pf_hurt_t, -1) >= time('now') - time('15 m')"), m("u_pf_hurt_t > pf_rk_vbest")]}),
    # ---------------------------------------------------------------- Reckoning pass 2: nightmares, portal storms
    eoc("PF_RK_night_tick", [
        {"run_eocs": "PF_THREAT_scan"},
        {"if": m("pf_threat == 0"), "then": [{"run_eocs": "PF_RK_nm_try"}]},
    ], "Once an hour, 01:00-04:00, until someone has had a nightmare tonight: someone frightened in the last day (hurt, carried off in an alarm, caught in a portal storm) or in mourning may wake up screaming.",
        recurrence="1 hours", **{"global": True},
        condition={"and": [m("time_since('midnight', 'unit': 'hours') >= 1"), m("time_since('midnight', 'unit': 'hours') < 4"),
                           m(f"value_or(pf_nm_night, -1) != {TODAY}")]}),
    eoc("PF_RK_nm_try", [
        {"u_location_variable": g("pf_nm_av")}, m("pf_nm_best = -1"),
        {"u_run_npc_eocs": ["PF_RK_nm_cand"], "local": True, "npc_range": 30},
        {"if": {"and": [m("pf_nm_best >= 0"), {"or": [m("rand(1) == 0"), m("value_or(pf_nm_force, 0) == 1")]}]}, "then": [{"run_eocs": "PF_RK_nm_do"}]},
    ], "u = avatar."),
    eoc("PF_RK_nm_cand", [
        m("_s = rand(100) + (u_has_trait('PF_CHILD') ? 60 : 0)"),
        {"if": m("_s > pf_nm_best"), "then": [
            m("pf_nm_best = _s"), {"u_set_talker": g("pf_nm_who")}, name_into("pf_nm_name"),
            {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_nm_uid")},
            {"u_location_variable": g("pf_nm_pos")},
            m("pf_nm_kid = 0"), {"if": {"u_has_trait": "PF_CHILD"}, "then": [m("pf_nm_kid = 1")]},
            m("pf_nm_band = value_or(u_pf_band, 0)"),
            {"set_string_var": "none", "target_var": g("pf_nm_mom")}, {"set_string_var": "none", "target_var": g("pf_nm_dad")}, {"set_string_var": "none", "target_var": g("pf_nm_grd")},
            {"if": m("has_var(u_pf_mom)"), "then": [{"copy_var": {"u_val": "pf_mom"}, "target_var": g("pf_nm_mom")}, {"copy_var": {"u_val": "pf_dad"}, "target_var": g("pf_nm_dad")}]},
            {"if": m("has_var(u_pf_guardian)"), "then": [{"copy_var": {"u_val": "pf_guardian"}, "target_var": g("pf_nm_grd")}]}]},
    ], "u = someone near you.  Children are the likeliest to have the nightmare.  Whoever is awake on watch (yours or the town's) can't have one (full run: \"kept watch through the night\" and \"cries out in their sleep\" the same night).",
        condition={"and": [m("has_var(u_pf_uid)"), {"not": {"u_has_effect": "PF_infant"}},
                           {"not": {"and": [m("value_or(pf_watch_active, 0) == 1"), {"compare_string": [{"u_val": "pf_uid"}, g("pf_watch_uid")]}]}},
                           {"not": ON_WATCH},
                           {"not": {"and": [m("value_or(pf_nm_adult_only, 0) == 1"), {"u_has_trait": "PF_CHILD"}]}},
                           {"or": [m("value_or(u_pf_fright_t, -1) >= time('now') - time('1 d')"), m("time('now') < value_or(u_pf_mourn_until, 0)")]}]}),
    eoc("PF_RK_nm_do", [
        m(f"pf_nm_night = {TODAY}"), m("pf_nightmares_total = value_or(pf_nightmares_total, 0) + 1"),
        {"copy_var": g("pf_nm_name"), "target_var": g("pf_say_b")},
        m("pf_nm_c = 0"),
        {"if": {"and": [m("pf_nm_kid == 1"), {"or": [{"compare_string": [g("pf_nm_mom"), "AVATAR"]}, {"compare_string": [g("pf_nm_dad"), "AVATAR"]}, {"compare_string": [g("pf_nm_grd"), "AVATAR"]}]}]},
         "then": [m("pf_nm_c = 2")]},
        # full run days 124-127: one of Dante's four grieving children woke him every night.  If your child woke you last night,
        # someone else who cares goes this time (Mitzi, a housemate); you're woken only if there's nobody.
        {"if": {"and": [m("pf_nm_c == 2"), m(f"value_or(pf_nm_you_day, -9) >= {TODAY} - 1")]}, "then": [
            m("pf_nm_cb = -1"),
            {"u_run_npc_eocs": ["PF_RK_nm_comforter"], "local": True, "npc_range": 40},
            {"if": m("pf_nm_cb >= 0"), "then": [m("pf_nm_c = 1")]}]},
        {"if": m("pf_nm_c == 0"), "then": [
            m("pf_nm_cb = -1"),
            {"u_run_npc_eocs": ["PF_RK_nm_comforter"], "local": True, "npc_range": 40},
            {"if": m("pf_nm_cb >= 0"), "then": [m("pf_nm_c = 1")]}]},
        {"if": m("pf_nm_c == 2"), "then": [
            {"if": {"u_has_effect": "sleep"}, "then": [{"u_lose_effect": "sleep"}, {"u_lose_effect": "lying_down"}, {"u_lose_effect": "PF_sleep_easy"}]},
            m(f"pf_nm_you_day = {TODAY}"), line("nm_kid_you"), m("pf_m_str_in = 40"), {"run_eocs": "PF_MK_parenting", "alpha_talker": "avatar", "beta_talker": g("pf_nm_who")}]},
        {"if": m("pf_nm_c == 1"), "then": [
            {"if": m("pf_nm_kid == 1"),
             "then": [line("nm_kid"), m("pf_m_str_in = 40"), {"run_eocs": "PF_MK_parenting", "alpha_talker": g("pf_nm_comf"), "beta_talker": g("pf_nm_who")}],
             "else": [line("nm_adult"), m("pf_m_str_in = 45"), {"run_eocs": "PF_MK_care_given", "alpha_talker": g("pf_nm_comf"), "beta_talker": g("pf_nm_who")}]}]},
        {"if": m("pf_nm_c == 0"), "then": [line("nm_alone")]},
    ], "u = avatar.  The nightmare: your own child wakes you (you go to them); otherwise their parent, or whoever cares most about them within 20 tiles, sits with them (a parenting or care moment).  Nobody: they cry it out alone."),
    eoc("PF_RK_nm_comforter", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_nm_pos) <= 20"), "then": [
            {"copy_var": g("pf_nm_uid"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
            m("_s = pf_read_w"),
            {"if": {"or": [{"compare_string": [{"u_val": "pf_uid"}, g("pf_nm_mom")]}, {"compare_string": [{"u_val": "pf_uid"}, g("pf_nm_dad")]},
                           {"compare_string": [{"u_val": "pf_uid"}, g("pf_nm_grd")]}]}, "then": [m("_s += 100")]},
            {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("_s += 15")]},
            {"if": m("(value_or(u_pf_resident, 0) == 1) + (value_or(u_pf_band, 0) > 0) * (value_or(u_pf_band, 0) == pf_nm_band) > 0"), "then": [m("_s += 10")]},
            {"if": {"and": [m("_s >= (pf_nm_kid == 1 ? 5 : 15)"), m("_s > pf_nm_cb")]}, "then": [m("pf_nm_cb = _s"), {"u_set_talker": g("pf_nm_comf")}, name_into("pf_say_a")]}]},
    ], "u = someone who might go to them: a parent first, then whoever cares most (warmth 15+; for a screaming child 5+ is enough, and housemates and bandmates count a little extra).",
        condition={"and": [ADULT, m("has_var(u_pf_uid)"), {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_nm_uid")]}}]}),
    # full run day 117: "The sky goes wrong…", "The sky closes up again…" and "The sky goes wrong…" again within the hour: the
    # storm's stages (early, then close) have a gap of ordinary weather between them.  It's over after 30 calm minutes.
    eoc("PF_RK_storm_tick", [
        {"if": STORMY, "then": [m("pf_ps_calm_t = -1")]},
        # full run day 168: the early warning at 02:57, more than 30 calm minutes, then the close storm at 05:30 ("closes up
        # again" in between).  After only the early stage, the end waits up to 6 calm hours for the storm itself.
        {"if": {"or": [{"is_weather": w} for w in ("distant_portal_storm", "close_portal_storm", "portal_storm", "strong_portal_storm")]},
         "then": [m("pf_ps_main = 1")]},
        {"if": {"and": [STORMY, m("value_or(pf_ps_on, 0) == 0")]}, "then": [{"run_eocs": "PF_RK_storm_start"}],
         "else": [{"if": {"and": [{"not": STORMY}, m("value_or(pf_ps_on, 0) == 1")]}, "then": [
             {"if": m("value_or(pf_ps_calm_t, -1) < 0"), "then": [m("pf_ps_calm_t = time('now')")],
              "else": [{"if": m("time('now') - pf_ps_calm_t >= (value_or(pf_ps_main, 0) == 1 ? time('30 m') : time('6 h'))"), "then": [m("pf_ps_calm_t = -1"), m("pf_ps_main = 0"), {"run_eocs": "PF_RK_storm_end"}]}]}]}]},
    ], "Every 5 minutes: notices a portal storm beginning and ending (vanilla weather; personal_portal_storms only changes who the storm's creatures attack).  The end needs 30 minutes without storm weather.",
        recurrence="5 minutes", **{"global": True}),
    eoc("PF_RK_storm_start", [
        m("pf_ps_on = 1"), m("pf_ps_t = time('now')"), m("pf_ps_n = 0"),
        {"u_run_npc_eocs": ["PF_RK_storm_mark"], "local": True, "npc_range": 30},
        {"if": {"and": [m("pf_ps_n > 0"), m(CALM_LINES)]}, "then": [{"copy_var": g("pf_ps_first"), "target_var": g("pf_say_a")}, line("storm_start")]},
    ], "u = avatar.  The sky goes wrong: everyone near is frightened, and the first adult found herds people together."),
    eoc("PF_RK_storm_mark", [
        m("u_pf_fright_t = time('now')"),
        {"if": {"and": [ADULT, m("pf_ps_n == 0"), {"not": {"u_has_effect": "sleep"}}]}, "then": [name_into("pf_ps_first")]},
        {"if": ADULT, "then": [m("pf_ps_n += 1")]},
    ], condition=m("has_var(u_pf_uid)")),
    eoc("PF_RK_storm_end", [
        m("pf_ps_on = 0"), m("pf_ps_n = 0"),
        {"u_run_npc_eocs": ["PF_RK_storm_after"], "local": True, "npc_range": 30},
        {"if": m("pf_ps_n > 0"), "then": [
            m(f"pf_rk_storm_day = {TODAY}"), m("pf_storms_total = value_or(pf_storms_total, 0) + 1"),
            {"if": m(CALM_LINES), "then": [{"copy_var": g("pf_ps_first"), "target_var": g("pf_say_a")}, line("storm_end")]}]},
    ], "u = avatar.  The storm passes: everyone who went through it with you shares the danger (a shared_danger moment with you), and it'll be talked about tonight."),
    eoc("PF_RK_storm_after", [
        m("u_pf_fright_t = time('now')"),
        {"if": {"and": [ADULT, m("pf_ps_n == 0")]}, "then": [name_into("pf_ps_first")]},
        {"if": ADULT, "then": [m("pf_ps_n += 1"), m("pf_m_str_in = 50"), {"run_eocs": "PF_MK_shared_danger", "beta_talker": "avatar"}]},
    ], condition=m("has_var(u_pf_uid)")),
    # ---------------------------------------------------------------- the fight, retold at the fire
    eoc("PF_RK_retell", [
        m(f"pf_rk_told_day = {TODAY}"),
        {"copy_var": g("pf_rk_hero"), "target_var": g("pf_say_a")}, {"copy_var": g("pf_rk_hsaved"), "target_var": g("pf_say_b")},
        {"if": m(f"value_or(pf_rk_day, -1) != {TODAY}"), "then": [line("storm_retell")],
         "else": [{"if": m("pf_rk_hero_av == 1"), "then": [line("rk_retell_you")],
                   "else": [{"if": m("pf_rk_saved_av == 1"), "then": [line("rk_retell_saved")],
                             "else": [{"if": m("value_or(pf_fire_n, 0) <= 1"), "then": [line("rk_retell_two")], "else": [line("rk_retell")]}]}]}]},
        {"u_add_morale": "PF_morale_alive", "bonus": 10, "max_bonus": 10, "duration": "8 hours", "decay_start": "4 hours"},
    ], "u = avatar, at the evening beat (fire or home) on a day with a rescue, unless the fight broke up this very evening (then nobody talks, the bottle goes around).",
        condition={"and": [{"or": [m(f"value_or(pf_rk_day, -1) == {TODAY}"), m(f"value_or(pf_rk_storm_day, -1) == {TODAY}")]},
                           m(f"value_or(pf_rk_told_day, -1) != {TODAY}")]}),
]

# ============================================================ LINES
LINES = {
    "home_set":    ("You decide this is home.  It isn't much, but it's yours.", "good"),
    "home_move":   ("Home is here now.", "good"),
    "home_forget": ("This isn't home anymore.", "info"),
    "home_here":   ("You're home.  <global_val:pf_hm_restxt> moved in with you so far.", "info"),
    "home_far":    ("Home is <global_val:pf_hm_dist> steps from here.  <global_val:pf_hm_restxt> moved in with you so far.", "info"),
    "breakfast":   ("You wake to the smell of cooking.  <global_val:pf_say_a> has made <global_val:pf_say_b>, and there's coffee.", "good"),
    "breakfast_1": ("<global_val:pf_say_a> is already up.  There's <global_val:pf_say_b> waiting for you, and a mug of coffee going cold next to it.", "good"),
    "breakfast_back": ("<global_val:pf_say_a> calls you over: <global_val:pf_say_b>, and a mug of coffee.  \"You look like you walked all night.  Sit, eat.\"", "good"),
    "breakfast_awake": ("<global_val:pf_say_a> calls you over: <global_val:pf_say_b>, and a mug of coffee.  \"You were up before any of us.  Sit, eat.\"", "good"),
    "breakfast_late": ("You slept half the day.  <global_val:pf_say_a> kept <global_val:pf_say_b> warm for you anyway, and makes a fresh pot of coffee without a word.", "good"),
    "breakfast_2": ("Somebody nudges you awake with a mug of coffee.  <global_val:pf_say_a> has made <global_val:pf_say_b>.  \"Eat.  Before it's gone.\"", "good"),
    "invite_yes":  ("<global_val:pf_say_a> looks at you for a long moment.  \"A roof.  People.  Yeah.  Yeah, I'd like that.\"", "good"),
    "invite_band_yes": ("<global_val:pf_say_a> talks it over with the others, and they come back smiling.  \"We're tired of walking.  We'll come.\"", "good"),
    "pass_by_first": ("<global_val:pf_say_a> and the people they travel with stop when they see you, hands where you can see them.  Somebody passes round a strip of jerky; somebody asks about the road ahead.  Names are traded.", "info"),
    "pass_by_again": ("<global_val:pf_say_a>'s band again.  This time they sit down for a while, share what they've got, and tell you where the dead are thick.", "good"),
    "invite_stranger_one": ("<global_val:pf_say_a> shakes their head.  \"I don't know you.  No offense.\"", "info"),
    "invite_stranger": ("<global_val:pf_say_a> shakes their head.  \"We don't know you.  No offense.\"", "info"),
    "invite_known_one": ("<global_val:pf_say_a> considers it, then shakes their head.  \"I hardly know you yet.  Ask me again in a while.\"", "info"),
    "invite_known": ("<global_val:pf_say_a> glances back at the others and shakes their head.  \"We hardly know you yet.  Ask us again in a while.\"", "info"),
    "invite_warming_one": ("<global_val:pf_say_a> almost smiles.  \"You're growing on me.  Give it a few more days.\"", "info"),
    "invite_warming": ("<global_val:pf_say_a> looks back at the others.  \"You're growing on us.  Give it a few more days.\"", "info"),
    "invite_trust": ("<global_val:pf_say_a> hesitates.  \"Ask me again some other time.  I'm not ready to trust anyone that much.\"", "info"),
    "distant":     ("Somewhere far off, you hear voices.  Someone laughs.", "info"),
    "horn_alarm_1": ("<global_val:pf_hn_spot> bangs on a pot.  \"Dead coming!  Everybody up!\"", "bad"),
    "horn_alarm_2": ("<global_val:pf_hn_spot> shouts: \"Company!  Weapons, now!\"", "bad"),
    "horn_alarm_3": ("<global_val:pf_hn_spot> whistles, two short and one long: the dead are here.", "bad"),
    "horn_alarm":  ("<global_val:pf_hn_spot> shouts: \"Up!  Up!  They're here!\"", "bad"),
    "hurt_wake_you": ("A scream close by jerks you awake: <global_val:pf_say_a> is fighting something, and losing.", "bad"),
    "horn_wake_you": ("Someone is shaking you.  \"Get up.  Get up, they're here.\"", "bad"),
    "horn_shield": ("<global_val:pf_say_a> grabs <global_val:pf_say_b> and runs, keeping themselves between the kid and the noise.", "bad"),
    # full run: the same line every alarm; four ways to say it
    "horn_shield_1": ("<global_val:pf_say_a> scoops up <global_val:pf_say_b> without a word and heads for cover.", "bad"),
    "horn_shield_2": ("<global_val:pf_say_a> has <global_val:pf_say_b> by the wrist and is already moving, low and fast, away from it.", "bad"),
    "horn_shield_3": ("\"With me.  Now.\"  <global_val:pf_say_a> hustles <global_val:pf_say_b> off, one hand on the back of the kid's head.", "bad"),
    "horn_clear":  ("It's quiet again.  People count heads.  Everyone's still here.", "good"),
    "horn_lull": ("A lull.  Nobody lowers their weapon; there'll be more of them before this is over.", "info"),
    "horn_clear_hurt": ("It's quiet again.  People count heads: everyone's here, but not everyone's whole.  Someone is shouting for bandages for <global_val:pf_hn_hurt_a>.", "bad"),
    "horn_clear_grief": ("It's quiet again.  People count heads, and stop where the count used to go on.", "info"),
    "horn_clear_loss": ("It's quiet again.  People count heads, and nobody says the names out loud until they're sure.", "bad"),
    'rk_clings': ("<global_val:pf_say_b> won't let go of <global_val:pf_say_a>'s hand for the rest of the <global_val:pf_rk_part>.", 'info'),
    'rk_clings_you': ("<global_val:pf_say_b> won't let go of your hand for the rest of the <global_val:pf_rk_part>.", 'info'),
    'newcomer_home': ("<global_val:pf_say_a> walks in at the gate with everything they own on their back.  Somebody shows them where to put it.", 'good'),
    'newcomer_baby': ("<global_val:pf_say_a> is carried in at the gate, asleep, and passed from arm to arm.", 'good'),
    'newcomer_kid': ("<global_val:pf_say_a> comes in at the gate holding somebody's hand, and stares at everything.", 'good'),
    'stray_home': ("<global_val:pf_say_a> turns up at the gate, soaked through and quiet, a day late.  Nobody asks where they've been.", 'info'),
    'rk_tended': ("<global_val:pf_say_a> cleans <global_val:pf_say_b>'s wounds and wraps them, muttering the whole time.", 'good'),
    'rk_ran': ("<global_val:pf_say_a> ran when it started.  <global_val:pf_say_b> hasn't said a word about it, which is worse.", "bad"),
    'rk_ran_you': ("<global_val:pf_say_a> ran when that thing had you.  Now they won't look at you.", "bad"),
    'nm_kid_you': ("In the night, <global_val:pf_say_b> wakes up screaming.  You're there before you're properly awake, and you stay until they're asleep again.", 'info'),
    'nm_kid': ('In the night, <global_val:pf_say_b> wakes up screaming.  <global_val:pf_say_a> is there before anyone else, holding them until it passes.', 'info'),
    'nm_adult': ('In the night, <global_val:pf_say_b> wakes up shouting.  <global_val:pf_say_a> sits with them in the dark until their breathing slows.', 'info'),
    'band_cry_kid': ("<global_val:pf_bh_who> screams.  <global_val:pf_bh_resc> is already running toward them.", 'bad'),
    'band_cry': ("<global_val:pf_bh_who> shouts for help.  <global_val:pf_bh_resc> goes to them.", 'bad'),
    'nm_alone': ('In the night, <global_val:pf_say_b> cries out in their sleep, and nobody goes to them.  Nobody mentions it in the morning.', 'bad'),
    'storm_start': ('The sky goes wrong.  <global_val:pf_say_a> starts herding everyone together without a word.', 'bad'),
    'storm_end': ('The sky closes up again.  For a long time nobody says anything.  Then <global_val:pf_say_a> laughs, shakily, and everyone starts talking at once.', 'info'),
    'storm_retell': ("Everyone has a different story about what they saw in the storm.  None of them match, and nobody laughs at anyone's.", 'info'),
    'rk_retell': ("<global_val:pf_say_a> doesn't want to talk about the fight, so everyone else does.  By the third telling there were five of them.", 'good'),
    'rk_retell_two': ("<global_val:pf_say_a> doesn't want to talk about the fight, so you tell it, and they correct every detail.  By the end there were five of them.", 'good'),
    'rk_retell_you': ("Somebody tells the story of the fight again, the part where you came for <global_val:pf_say_b>.  It's a better story every time.", 'good'),
    'rk_retell_saved': ('Someone tells how <global_val:pf_say_a> came for you.  You let them tell it.', 'good'),
    "roster":      ("<global_val:pf_say_a>: <global_val:pf_say_b>.", "info"),
    "roster_none": ("Nobody who lives with you is around.", "info"),
    "cook_fill": ("Nobody's been cooking.  <global_val:pf_say_a> looks at the cold pot for a while, then rolls up their sleeves.  \"Fine.  Me, then.\"", "info"),
    "role_change": ("<global_val:pf_say_a> shrugs.  \"Fine.  I'll be the <global_val:pf_say_b> from now on.\"", "info"),
    "chore_lamp":  ("<global_val:pf_say_a> sets a candle by the stores, so nobody has to feel around for the water in the dark.", "info"),
    "chore_cook":  ("<global_val:pf_say_a> has a pot of soup going.  There's enough for everyone.", "good"),
    "chore_cook_1": ("<global_val:pf_say_a> is cooking.  Whatever it is, it smells better than it has any right to.", "good"),
    "chore_cook_2": ("<global_val:pf_say_a> sends someone out for more water and keeps stirring.  \"It'll be ready when it's ready.\"", "good"),
    "chore_cook_3": ("<global_val:pf_say_a> sets out bowls at home.  Nobody has to ask twice.", "good"),
    "chore_guard_1": ("<global_val:pf_say_a> climbs up somewhere high and watches the road for an hour.", "info"),
    "chore_guard_2": ("<global_val:pf_say_a> drags a broken car door across a gap in the fence and wires it in place.", "info"),
    "chore_forage_1": ("<global_val:pf_say_a> is back with <global_val:pf_say_b>, and a scratch on one arm they don't want to talk about.", "good"),
    "chore_forage_2": ("<global_val:pf_say_a> empties <global_val:pf_say_b> onto the table, pleased with themselves.", "good"),
    "chore_tinker_1": ("<global_val:pf_say_a> gets a dead flashlight working again with parts from two others.", "info"),
    "chore_tinker_2": ("<global_val:pf_say_a> sharpens every blade in the place, one after another, humming.", "info"),
    "chore_guard": ("<global_val:pf_say_a> walks the edge of the place, checking every gap in the fence.", "info"),
    "chore_forage": ("<global_val:pf_say_a> comes back from the woods with <global_val:pf_say_b>.", "good"),
    "chore_tinker": ("<global_val:pf_say_a> spends the afternoon fixing a door that's been sticking for a week.  It doesn't stick anymore.", "info"),
    "chore_carer": ("<global_val:pf_say_a> keeps an eye on <global_val:pf_say_b> for hours, and gets them to eat something green.", "info"),
    "bedtime":     ("The house goes quiet for the night.  Somebody is snoring already.", "info"),
    "unpack":      ("<global_val:pf_say_a> unpacks at home: what's left of their food, and the things they carried all this way.", "good"),
    "rumor":       ("<global_val:pf_rm_text>", "info"),
    "practice":    ("<global_val:pf_say_a> is getting good at this.", "info"),
    "burnt_alone": ("<global_val:pf_say_a> burned the soup.  Nobody says anything, but everybody eats less.", "bad"),
    "burnt_row":   ("<global_val:pf_say_b> burned the soup again.  <global_val:pf_say_a> has opinions about that, loudly, and <global_val:pf_say_b> has opinions about <global_val:pf_say_a>.", "bad"),
    "leaves":      ("<global_val:pf_say_a> packs their things.  \"This isn't working.  I'm going.\"  Nobody stops them.", "bad"),
    "hosted":      ("<global_val:pf_say_a> waves you over from their doorway.  \"Come in, sit down.  You look half-starved.\"  There's soup, and nobody asks you for anything.", "good"),
    "visit":       ("<global_val:pf_say_a>'s family comes over from their place, carrying something wrapped in a cloth.  \"We brought food.  Thought you might like company.\"", "good"),
    "rumor_list":  ("<global_val:pf_rl_text>  (<global_val:pf_rl_ago> days ago)", "info"),
    "rumor_list_today": ("<global_val:pf_rl_text>  (today)", "info"),
    "rumor_none":  ("Nobody has mentioned anyone else out there yet.", "info"),
}
# ============================================================ v0.8 HOUSEKEEPING: the stores and everyone's corner
# The user (2026-10-14): "I don't like the way NPCs scatter their items everywhere on the ground without being organised.
# Public food somewhere, personal floor space somewhere else."  Every communal spawn (the cook's pot, water, breakfast,
# deliveries, harvests, forage, eggs, milk, market goods) went to pf_home_loc, the same tile everyone idles on; dishes piled
# up with every meal; each night everyone rolled a new random patch of floor; a dead resident's things lay where they fell
# (and asked "considered stealing").  Now:
#   the stores (pf_stores_loc): one place for the household's food, water and supplies.  Picked once (a rack, counter,
#     cupboard or locker near home), or wherever you say (Home: "Keep the stores here").  Every communal spawn goes there.
#   corners (u_pf_corner): each grown-up who lives here has their own spot (a bed if there's a free one, else a patch of floor
#     3-6 tiles from home, never on the stores), kept from night to night.  They sleep there; what they brought is unpacked
#     there.  Yours (pf_av_corner) is wherever you say (Home: "This is my corner"); nobody tidies it.
#   tidying: every 3 hours by day, someone who lives here washes the empty dishes and carries stray food, drink, medicine and
#     seed back to the stores.  Nothing in anyone's corner is touched.
#   estates: a couple of hours after one of ours dies, someone gathers up their things (where they fell, and their corner)
#     and puts them with the stores (engine patch 15: they stop belonging to the dead).
#   gifts handed to you (a child's marble, tea, a keepsake, something sweet) go into your hands, not on the floor.
STORES = g("pf_stores_loc")
STORE_FURN = ["f_rack", "f_counter", "f_cupboard", "f_locker", "f_dresser", "f_crate_o", "f_bookcase"]
CN_MAX = 16
DISHES = [("ceramic_bowl", 405000), ("ceramic_mug", 348000), ("jug_plastic", 190000)]   # empty below this weight (mg)
# Kinfold day 133: water in plastic bottles stayed on the floor (a bottle's own category is "container", not food)
DRINK_CONTAINERS = ["bottle_plastic", "bottle_plastic_small", "bottle_glass", "bottle_twoliter", "jar_glass_sealed",
                    "jar_3l_glass_sealed", "can_drink", "canteen", "flask_glass"]
NEAR_CORNER = {"or": [{"and": [m(f"value_or(pf_cnl_n, 0) > {k}"), m(f"distance('npc', pf_cnl_{k}) <= 1")]} for k in range(CN_MAX)] +
                     [{"and": [m("has_var(pf_av_corner)"), m("distance('npc', pf_av_corner) <= 1")]}]}
KEEP_OK = {"not": NEAR_CORNER}
ROTTEN = {"npc_has_flag": "PF_ROTTEN"}   # engine patch 16; guard with pf_eng_level >= 16
HOUR_H = "time_since('midnight', 'unit': 'hours')"
TODAY_H = "floor(time('now') / time('1 d'))"

def stores_next(i):
    return [{"run_eocs": f"PF_STORES_try_{i + 1}"}] if i + 1 < len(STORE_FURN) else []
stores_steps = [eoc(f"PF_STORES_try_{i}", [
    {"u_location_variable": g("pf_sp_at"), "furniture": STORE_FURN[i], "target_max_radius": 15,
     "true_eocs": [{"id": f"PF_STORES_hit_{i}", "effect": [
         {"if": m("distance(pf_sp_at, pf_home_loc) <= 10"),
          "then": [{"copy_var": g("pf_sp_at"), "target_var": STORES}, m("pf_stores_set = 1"),
                   {"if": m(CALM_LINES), "then": [line("stores_auto")]}],
          "else": stores_next(i)}]}],
     "false_eocs": [{"id": f"PF_STORES_miss_{i}", "effect": stores_next(i)}]}],
    f"u = avatar.  Step {i} of choosing the stores: a {STORE_FURN[i]} within 10 tiles of home?") for i in range(len(STORE_FURN))]

corner_claims = [{"if": {"and": [m(f"value_or(pf_cnl_n, 0) > {k}"), m(f"distance(u_pf_corner, pf_cnl_{k}) < 2")]}, "then": [m("pf_cn_ok = 0")]}
                 for k in range(CN_MAX)]
STORES_GONE = {"or": [m("has_var(pf_stores_loc) == 0"), m("distance(pf_stores_loc, pf_home_loc) > 30")]}
house = [
    eoc("PF_STORES_ensure", [
        {"copy_var": g("pf_home_loc"), "target_var": STORES}, m("pf_stores_set = 0"),
    ], "The stores start at home itself until a better place is found (or you choose one).  Also when home moves far away.",
        condition={"and": [m(AT_HOME), STORES_GONE]}),
    eoc("PF_STORES_migrate", [{"run_eocs": "PF_STORES_ensure"}], "Saves from before v0.8: the stores appear within a minute.",
        recurrence="1 minutes", **{"global": True}, condition={"and": [m(AT_HOME), STORES_GONE]}),
    eoc("PF_STORES_pick", [
        {"u_location_variable": g("pf_hm_av")},
        {"if": m("distance(pf_hm_av, pf_home_loc) <= 15"), "then": [{"run_eocs": "PF_STORES_try_0"}]},
    ], "Once, when you're home: the household settles on a rack, counter, cupboard or locker within 10 tiles of home for the stores (open shelves first, so the food can be seen).",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m("has_var(pf_stores_loc)"), m("value_or(pf_stores_set, 0) == 0")]}),
    eoc("PF_HOUSE_stores_here", [
        {"u_location_variable": STORES}, m("pf_stores_set = 2"), line("stores_here"),
        m("pf_td_force = 1"), {"run_eocs": "PF_HOUSE_tidy_do"}, m("pf_td_force = 0"),
    ], "u = avatar (Home menu).", condition={"and": [m(AT_HOME), m("value_or(pf_hm_dist, 99) <= 20")]}),
    eoc("PF_HOUSE_corner_here", [
        {"u_location_variable": g("pf_av_corner")}, line("corner_you"),
    ], "u = avatar (Home menu).", condition={"and": [m(AT_HOME), m("value_or(pf_hm_dist, 99) <= 20")]}),
    # ---------------------------------------------------------------- corners
    eoc("PF_HOUSE_corners_collect", [
        m("pf_cnl_n = 0"),
        {"u_run_npc_eocs": [{"id": "PF_HOUSE_corner_note", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), m("has_var(u_pf_corner)")]},
                             "effect": [{"if": m(f"pf_cnl_n < {CN_MAX}"), "then": [
                                 {"set_string_var": "pf_cnl_<global_val:pf_cnl_n>", "target_var": ctx("cr"), "parse_tags": True},
                                 {"copy_var": {"u_val": "pf_corner"}, "target_var": {"var_val": "cr"}}, m("pf_cnl_n += 1")]}]}],
         "local": True, "npc_range": 60},
    ], "u = avatar.  pf_cnl_0.. = the corners of everyone who lives here (in the bubble)."),
    eoc("PF_HOUSE_corner_assign", [
        {"if": {"or": [m("has_var(u_pf_corner) == 0"), m("distance(u_pf_corner, pf_home_loc) > 30")]}, "then": [
            {"if": m("has_var(u_pf_house)"),
             "then": [{"copy_var": {"u_val": "pf_house"}, "target_var": {"u_val": "pf_corner"}},
                      {"location_variable_adjust": {"u_val": "pf_corner"}, "x_adjust": m("rand(2) - 1"), "y_adjust": m("rand(2) - 1")}],
             "else": [
                {"run_eocs": "PF_HOUSE_corners_collect", "alpha_talker": "avatar"},
                m("pf_cn_ok = 0"),
                {"u_location_variable": {"u_val": "pf_corner"}, "furniture": "f_bed", "target_max_radius": 20,
                 "true_eocs": [{"id": "PF_HOUSE_corner_bed", "effect": [m("pf_cn_ok = 1")] + corner_claims}]},
                {"if": m("pf_cn_ok == 0"), "then": [
                    {"copy_var": g("pf_home_loc"), "target_var": {"u_val": "pf_corner"}},
                    m("_cx = (rand(1) * 2 - 1) * (3 + rand(3))"), m("_cy = rand(6) - 3"),
                    {"location_variable_adjust": {"u_val": "pf_corner"}, "x_adjust": m("_cx"), "y_adjust": m("_cy")},
                    {"if": {"and": [m("has_var(pf_stores_loc)"), m("distance(u_pf_corner, pf_stores_loc) <= 1")]}, "then": [
                        {"location_variable_adjust": {"u_val": "pf_corner"}, "y_adjust": 3}]}]}]}]},
    ], "u = a grown-up who lives here.  Their corner, kept from night to night: their family's house if they have one, else a free bed within 20 tiles (nobody else's), else a patch of floor 3-6 tiles from home that isn't the stores.",
        condition={"and": [m("value_or(u_pf_resident, 0) == 1"), m(AT_HOME)]}),
    # ---------------------------------------------------------------- tidying
    eoc("PF_HOUSE_tidy_tick", [
        {"u_location_variable": g("pf_hm_av")},
        {"if": m("distance(pf_hm_av, pf_home_loc) <= 30"), "then": [
            m("pf_td_t = time('now')"),
            {"run_eocs": "PF_THREAT_scan"},
            {"if": m("pf_threat == 0"), "then": [
                {"set_string_var": "", "target_var": g("pf_td_who")},
                {"u_run_npc_eocs": [{"id": "PF_HOUSE_tidier", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"),
                                                                                      {"not": {"u_has_effect": "sleep"}}, {"not": ON_WATCH}]},
                                     "effect": [{"if": {"compare_string": [g("pf_td_who"), ""]}, "then": [name_into("pf_td_who")]}]}],
                 "local": True, "npc_range": 30},
                {"if": {"not": {"compare_string": [g("pf_td_who"), ""]}}, "then": [{"run_eocs": "PF_HOUSE_tidy_do"}]}]}]},
    ], "Every 3 hours from 07:00 to 21:00, when you're home and it's calm: someone who lives here and is up tidies.  Nobody here, nobody tidies (your mess is yours).",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m("has_var(pf_stores_loc)"), m("time('now') - value_or(pf_td_t, -999999) >= time('3 h')"),
                           m(f"{HOUR_H} >= 7"), m(f"{HOUR_H} < 21")]}),
    eoc("PF_HOUSE_tidy_do", [
        {"run_eocs": "PF_HOUSE_corners_collect"},
        m("pf_td_n = 0"), m("pf_td_d = 0"), m("pf_td_rot = 0"), m("pf_td_bod = 0"), m("pf_td_bone = 0"),
        # engine patch 16: items answer PF_ROTTEN / PF_ZOMBIE_CORPSE (asking on the stock build is an error screen, so only then).
        # Full run: rotten cabbage sat in the stores for days, and the yard held 400 tainted bones and the dead from two sieges.
        {"run_eocs": "PF_ENGINE_caps"},
        {"if": m("value_or(pf_eng_level, 0) >= 16"), "then": [
            {"u_map_run_item_eocs": "all", "loc": g("pf_home_loc"), "min_radius": 0, "max_radius": 20,
             "search_data": [{"category": ["food"], "condition": {"and": [ROTTEN, KEEP_OK]}},
                             {"id": [it for it, w in DISHES], "condition": {"and": [ROTTEN, KEEP_OK]}}],
             "true_eocs": [{"id": "PF_HOUSE_throw_out", "effect": [m("pf_td_rot += 1"), "npc_die"]}]},
            {"u_map_run_item_eocs": "all", "loc": g("pf_home_loc"), "min_radius": 0, "max_radius": 20,
             "search_data": [{"id": "corpse", "condition": {"npc_has_flag": "PF_ZOMBIE_CORPSE"}}],
             "true_eocs": [{"id": "PF_HOUSE_burn_body", "effect": [m("pf_td_bod += 1"), "npc_die"]}]}]},
        {"u_map_run_item_eocs": "all", "loc": g("pf_home_loc"), "min_radius": 0, "max_radius": 20,
         "search_data": [{"id": ["bone_tainted", "skull_human_tainted"], "condition": KEEP_OK}],
         "true_eocs": [{"id": "PF_HOUSE_rake_bones", "effect": [m("pf_td_bone += 1"), "npc_die"]}]},
        {"if": {"and": [m("pf_td_rot + pf_td_bod + pf_td_bone > 0"), m(CALM_LINES)]}, "then": [
            {"if": m("pf_td_bod > 0"), "then": [line("tidy_bodies")], "else": [{"if": m("pf_td_bone > 0"), "then": [line("tidy_bones")]}]},
            {"if": m("pf_td_rot > 0"), "then": [line("tidy_rot")]}]},
        # wash up: the cook's empties (every meal brings its own bowl or mug; the empties are washed and go back to the kitchen)
        {"u_map_run_item_eocs": "all", "loc": g("pf_home_loc"), "min_radius": 0, "max_radius": 20,
         "search_data": [{"id": it, "condition": {"and": [m(f"n_weight() < {w}"), KEEP_OK]}} for it, w in DISHES],
         "true_eocs": [{"id": "PF_HOUSE_wash", "effect": [m("pf_td_d += 1"), "npc_die"]}]},
        # full run day 158: 37 mugs of cold coffee at the stores from before the morning count (nobody drinks them but you).
        # Keep four; the rest are poured out and washed.
        m("pf_td_cf = 0"),
        {"u_map_run_item_eocs": "all", "loc": STORES, "min_radius": 0, "max_radius": 2,
         "search_data": [{"id": "ceramic_mug", "condition": m("n_weight() >= 348000")}],
         "true_eocs": [{"id": "PF_HOUSE_pour_out", "effect": [m("pf_td_cf += 1"), {"if": m("pf_td_cf > 4"), "then": [m("pf_td_d += 1"), "npc_die"]}]}]},
        # put away: stray food, drink, medicine and seed (and full dishes and jugs) go back to the stores
        {"u_map_run_item_eocs": "all", "loc": STORES, "min_radius": 2, "max_radius": 20,
         "search_data": [{"category": ["food", "drugs", "seeds"], "condition": KEEP_OK},
                         {"id": [it for it, w in DISHES] + DRINK_CONTAINERS, "condition": KEEP_OK}],
         "true_eocs": [{"id": "PF_HOUSE_put_away", "effect": [m("pf_td_n += 1"), {"npc_teleport": STORES}]}]},
        {"if": {"and": [m("pf_td_n + pf_td_d > 0"), m("value_or(pf_td_force, 0) == 0"), m(CALM_LINES),
                        m(f"value_or(pf_td_line_day, -1) != {TODAY_H}")]}, "then": [
            m(f"pf_td_line_day = {TODAY_H}"),
            m("_p = rand(2)"), {"if": m("_p == value_or(pf_td_last, -1)"), "then": [m("_p = (_p + 1) % 3")]}, m("pf_td_last = _p"),
            {"if": m("_p == 0"), "then": [line("tidy_0")]}, {"if": m("_p == 1"), "then": [line("tidy_1")]}, {"if": m("_p == 2"), "then": [line("tidy_2")]}]},
        {"if": m("value_or(pf_td_force, 0) == 1"), "then": [line("stores_moved")]},
    ], "u = avatar.  One tidying pass.  Anything within a tile of someone's corner (or yours) is left alone."),
    # ---------------------------------------------------------------- estates
    eoc("PF_HOUSE_estate_tick", [
        {"u_location_variable": g("pf_hm_av")},
        {"if": m("distance(pf_hm_av, pf_est_at) <= 30"), "then": [
            {"run_eocs": "PF_THREAT_scan"},
            {"if": m("pf_threat == 0"), "then": [
                m("pf_est_pending = 0"), m("pf_est_n = 0"),
                {"set_string_var": "", "target_var": g("pf_td_who")},
                {"u_run_npc_eocs": [{"id": "PF_HOUSE_heir", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), {"not": {"u_has_effect": "sleep"}}]},
                                     "effect": [{"if": {"compare_string": [g("pf_td_who"), ""]}, "then": [name_into("pf_td_who")]}]}],
                 "local": True, "npc_range": 30},
                {"u_map_run_item_eocs": "all", "loc": g("pf_est_at"), "min_radius": 0, "max_radius": 1,
                 "search_data": [{"id_blacklist": ["corpse"]}],
                 "true_eocs": [{"id": "PF_HOUSE_estate_item", "effect": [m("pf_est_n += 1"), {"npc_teleport": STORES}]}]},
                {"if": m("value_or(pf_est_hascn, 0) == 1"), "then": [
                    {"u_map_run_item_eocs": "all", "loc": g("pf_est_cn"), "min_radius": 0, "max_radius": 1,
                     "search_data": [{"id_blacklist": ["corpse"]}],
                     "true_eocs": [{"id": "PF_HOUSE_estate_item_cn", "effect": [m("pf_est_n += 1"), {"npc_teleport": STORES}]}]}]},
                {"if": m("pf_est_n > 0"), "then": [
                    {"if": {"compare_string": [g("pf_td_who"), ""]}, "then": [line("estate_you")], "else": [line("estate")]}]}]}]},
    ], "A couple of hours after one of ours dies (and it's calm, and you're near): their things (where they fell, and their corner) go to the stores.  The household's now.",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m("value_or(pf_est_pending, 0) == 1"), m("has_var(pf_stores_loc)"),
                           m("time('now') - value_or(pf_est_t, 0) >= time('2 h')")]}),
] + [eoc(f"PF_GIVE_{key}", ([dict({"u_spawn_item": item, "suppress_message": True})] if not cont else
                           # Kinfold day 134: the morning coffee went into Dante's pack while he slept, and the game asked where to
                           # pour it ("would spill").  A drink or soup in an open mug or bowl is set down beside you.
                           [{"u_location_variable": ctx("gv")}, {"map_spawn_item": item, "loc": ctx("gv"), "container": cont}]),
         f"u = avatar.  {item} handed to you (solid things into your inventory; a drink or soup in an open dish beside you).")
     for key, item, cont in [("marble", "marble", None), ("chocolate", "chocolate", None), ("candy", "candy", None),
                             ("cookies", "cookies", None), ("tea", "tea", "ceramic_mug"), ("coffee", "coffee", "ceramic_mug"),
                             ("soup_meat", "soup_meat", "ceramic_bowl"), ("keepsake", "PF_carved_keepsake", None)]]
LINES.update({
    "stores_auto": ("From now on the food and water go in one place, on the shelves nearest home, where anyone can find them.", "info"),
    "stores_at_hand": ("The stores are right here, within reach.", "info"),
    "stores_dist": ("The stores are <global_val:pf_hm_sdist> steps <global_val:pf_hm_sdir> of you.  (Home: Keep the stores here, to move them.)", "info"),
    "stores_here": ("The stores go here from now on: food, water, medicine, anything the place shares.", "info"),
    "stores_moved": ("People start carrying the food and water over.", "info"),
    "corner_you": ("This is your corner.  Nobody will tidy what you leave here.", "info"),
    "tidy_rot": ("<global_val:pf_td_who> sniffs at the stores, makes a face and throws out what's turned.", "info"),
    "tidy_bodies": ("<global_val:pf_td_who> drags the dead out past the fence, one at a time, and burns them.  The smoke hangs over the place for an hour.", "info"),
    "tidy_bones": ("<global_val:pf_td_who> rakes the old bones out of the yard and tips them in the ditch.", "info"),
    "tidy_0": ("<global_val:pf_td_who> goes round with a basket: the food back with the stores, the dishes washed and stacked.", "info"),
    "tidy_1": ("<global_val:pf_td_who> clears up after everyone, muttering, and puts the food back where it lives.", "info"),
    "tidy_2": ("<global_val:pf_td_who> washes the bowls in a bucket and sets them out to dry.  The place looks lived in, not lived on.", "info"),
    "estate": ("<global_val:pf_td_who> gathers up <global_val:pf_est_name>'s things and puts them with the stores.  Nobody wants to be the one who decides what to keep.", "info"),
    "estate_you": ("You gather up <global_val:pf_est_name>'s things and put them with the stores.  It takes longer than it should.", "info"),
})
# full run day 139: raids, tribute and market day counted only pf_stores (the Keep's farm surplus, 0 in Kinfold) and
# said "the stores are bare" / "nothing to spare" beside shelves of oatmeal, soup and medicine.  When the surplus can't
# cover it, real food and medicine at the stores are drawn into it.  In: pf_dr_want (units wanted in pf_stores),
# pf_dr_div (at most a 1/div share of the shelf; 1 = all of it), pf_dr_all (1 = all or nothing).  u = avatar, home loaded.
STORE_GOODS = [{"category": ["food", "drugs"]}]
stores_draw = [
    eoc("PF_STORES_count", [
        m("pf_dr_real = 0"),
        {"if": {"and": [m("has_var(pf_stores_loc)")]}, "then": [
            {"u_location_variable": g("pf_dr_av")},
            {"if": m("distance(pf_dr_av, pf_stores_loc) <= 40"), "then": [
                {"u_map_run_item_eocs": "all", "loc": STORES, "min_radius": 0, "max_radius": 2, "search_data": STORE_GOODS,
                 "true_eocs": [{"id": "PF_STORES_count_one", "effect": [m("pf_dr_real += 1")]}]}]}]},
    ], "u = avatar.  pf_dr_real = how many food and medicine items are at the stores (0 when home isn't loaded)."),
    eoc("PF_STORES_draw", [
        m("pf_dr_got = 0"),
        {"if": m("value_or(pf_stores, 0) < pf_dr_want"), "then": [
            {"run_eocs": "PF_STORES_count"},
            m("pf_dr_need = min(pf_dr_want - value_or(pf_stores, 0), floor(pf_dr_real / max(value_or(pf_dr_div, 1), 1)))"),
            {"if": m("(value_or(pf_dr_all, 0) == 1) * (pf_dr_need < pf_dr_want - value_or(pf_stores, 0))"), "then": [m("pf_dr_need = 0")]},
            {"if": m("pf_dr_need > 0"), "then": [
                {"u_map_run_item_eocs": "all", "loc": STORES, "min_radius": 0, "max_radius": 2, "search_data": STORE_GOODS,
                 "true_eocs": [{"id": "PF_STORES_draw_one", "effect": [
                     {"if": m("pf_dr_got < pf_dr_need"), "then": [m("pf_dr_got += 1"), "npc_die"]}]}]},
                m("pf_stores = value_or(pf_stores, 0) + pf_dr_got")]}]},
        m("pf_dr_div = 1"), m("pf_dr_all = 0"),
    ], "u = avatar.  Tops pf_stores up toward pf_dr_want from the real stores (see above)."),
]
# full run day 150: courting a band away from home had nothing to give (supplies came only from the stores, within 40 tiles)
sack = [
    eoc("PF_HOUSE_pack_sack", [
        {"run_eocs": "PF_STORES_count"},
        {"if": m("pf_dr_real < 12"), "then": [say("There isn't enough in the stores to spare a sack.  (A dozen things to eat, and you near home.)")], "else": [
            m("pf_sk_took = 0"),
            {"u_map_run_item_eocs": "all", "loc": STORES, "min_radius": 0, "max_radius": 2, "search_data": [{"category": ["food"]}],
             "true_eocs": [{"id": "PF_HOUSE_sack_take", "effect": [{"if": m("pf_sk_took < 6"), "then": [m("pf_sk_took += 1"), "npc_die"]}]}]},
            # day 150: a 5 L sack fits no pocket (jacket pockets take 800 ml); it's slung over the shoulder instead
            {"u_spawn_item": "PF_supply_sack", "count": 1, "force_equip": True},
            say("You tie six things to eat from the stores up in a sack and sling it over your shoulder.  It's yours to give.")]},
    ], "u = avatar.  Home menu: a sack of supplies to carry to a band on the road.", condition=m(AT_HOME)),
    {"type": "ITEM", "subtypes": ["ARMOR"], "id": "PF_supply_sack", "name": {"str": "sack of supplies", "str_pl": "sacks of supplies"},
     "description": "Six things to eat from the stores at home, tied up in a sack and slung over the shoulder.  Give it to a band out on the road: generosity is remembered.",
     "weight": "3 kg", "volume": "5 L", "price": "0 cent", "price_postapoc": "0 cent", "material": ["cotton"], "symbol": "[", "color": "brown",
     "category": "other", "material_thickness": 1,
     "armor": [{"covers": ["torso"], "coverage": 5, "encumbrance": 4}],
     "flags": ["OVERSIZE", "BELTED", "WATER_FRIENDLY"]},
]
files["house.json"] = house + stores_steps + stores_draw + sack

files["lines.json"] = [eoc("PF_SAY_home", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Home lines, picked by the context var 'line'.")]

# ============================================================ HOME LAB
HL = [
    ("PF_HML_eve", "Evening: gather now; press again once they've sat down", "First press: resets tonight's evening and people head for the hearth (fire, or at home the table/couch).  Second press: the evening happens (wait a few minutes in between so they arrive).",
     [{"if": m("value_or(pf_eve_state, 0) == 1"),
       "then": [m("pf_eve_seat_t = time('now') - time('30 m')"), {"run_eocs": "PF_FIRE_look"}],
       "else": [m("pf_eve_day = -1"), m("pf_eve_done_day = -1"), {"run_eocs": "PF_FIRE_look"},
                {"if": m("value_or(pf_eve_state, 0) == 1"), "then": [say("[home lab] People are coming.  Wait a few minutes, then press again.")],
                 "else": [say("[home lab] Nobody gathered: no fire within 15 tiles, and no table, couch or armchair near home (or no home).")]}]}]),
    ("PF_HML_furnish", "Furnish: a table, a couch, a bookcase and a piano around you", "Places them 2-3 tiles around you on empty floor (or ground), so you can test an evening at home anywhere.",
     [{"u_location_variable": g("pf_hl_f")}] + [x for (fid, dx, dy) in (("PF_HML_t_table", 2, 0), ("PF_HML_t_sofa", -2, 0), ("PF_HML_t_book", 0, -3), ("PF_HML_t_piano", 0, 3)) for x in (
        {"copy_var": g("pf_hl_f"), "target_var": g("pf_hl_fx")}, {"location_variable_adjust": g("pf_hl_fx"), "x_adjust": dx, "y_adjust": dy},
        {"u_transform_radius": 0, "ter_furn_transform": fid, "target_var": g("pf_hl_fx")})] + [say("[home lab] A table, a couch, a bookcase and a piano.")]),
    ("PF_HML_props", "Evening: tonight everyone uses the props (needs furniture near)", "The second press of the entry above, but everyone's activity is a prop (reading, piano, cards) if the furniture is there, mourning or not.",
     [m("pf_prop_force = 1"),
      {"if": m("value_or(pf_eve_state, 0) == 1"),
       "then": [m("pf_eve_seat_t = time('now') - time('30 m')"), {"run_eocs": "PF_FIRE_look"}],
       "else": [say("[home lab] Gather people first (the entry above), wait for them to sit down, then use this instead of the second press.")]},
      m("pf_prop_force = 0")]),
    ("PF_HML_residents", "Residents: everyone who lives with you walks home now", "Runs the 30-minute resident step, ignoring the clock.",
     [{"u_run_npc_eocs": ["PF_HOME_resident_one"], "local": True, "npc_range": 60}, say("[home lab] Residents more than 20 tiles from home head back.")]),
    ("PF_HML_mods", "Mods: Mind Over Matter telepathy and Xedra discovery, on the nearest adult", "Needs those mods.  Telepathy: you are a telepath for a moment while the nearest adult (if they're yours or you care a lot) is badly hurt.  Xedra: the nearest adult finds out what you are, whether you are or not.",
     [m("pf_mi_test = 1"), m("pf_mi_mom_done = 0"), m("pf_mi_xe_done = 0"), say("[home lab] Mod tests armed: within a minute, if Mind Over Matter or Xedra Evolved is loaded, their test runs (wait a turn or two).")]),
    ("PF_HML_chores", "Household: jobs for everyone, then the chores now", "Gives a job to anyone who lives with you and has none, shows who does what, then runs the 3-hourly chores (ignoring the clock).",
     [{"u_run_npc_eocs": [{"id": "PF_HML_role_one", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), m("value_or(u_pf_role, 0) == 0")]}, "effect": [{"run_eocs": "PF_HOME_role_pick"}]}], "local": True, "npc_range": 60},
      {"run_eocs": "PF_HOME_roster"},
      m("pf_ch_l = 0"), {"u_location_variable": g("pf_hm_av")}, m("pf_ch_av = distance(pf_hm_av, pf_home_loc) <= 30"),
      {"u_run_npc_eocs": ["PF_HOME_chore_one"], "local": True, "npc_range": 60}]),
    ("PF_HML_bed", "Household: bedtime now (twice: claim beds, then sleep once there)", "Runs the night step ignoring the clock.  Press once, wait a few minutes for people to reach their beds, press again.",
     [m("pf_night = %s" % NIGHT),
      {"if": m("value_or(pf_bed_night, -1) != pf_night"), "then": [m("pf_bed_night = pf_night"), m("pf_bed_n = 0"), line("bedtime")]},
      {"u_run_npc_eocs": ["PF_HOME_bed_one"], "local": True, "npc_range": 60}]),
    ("PF_HML_rumor", "Rumor: tonight's evening, and someone tells you about a band out there", "Use instead of the second press of the first entry (gather first): the evening happens, and the rumor always comes up.  It runs inside the evening, right after the roll call, so it never uses a stale character id.",
     [m("pf_rm_force = 1"), m("pf_rm_none = 0"),
      {"if": m("value_or(pf_eve_state, 0) == 1"),
       "then": [m("pf_eve_seat_t = time('now') - time('30 m')"), {"run_eocs": "PF_FIRE_look"},
                {"if": m("pf_rm_none == 1"), "then": [say("[home lab] No living band is 80+ tiles away right now.")]}],
       "else": [say("[home lab] Gather people first (the first entry), wait for them to sit down, then use this.")]},
      m("pf_rm_force = 0")]),
    ("PF_HML_drift", "World: a day of drift for every band (settle or move on)", "Runs the daily drift five times now.",
     [{"run_eocs": "PF_WORLD_drift_tick"}, {"run_eocs": "PF_WORLD_drift_tick"}, {"run_eocs": "PF_WORLD_drift_tick"},
      {"run_eocs": "PF_WORLD_drift_tick"}, {"run_eocs": "PF_WORLD_drift_tick"},
      m("pf_hd_a = value_or(pf_world_settled_total, 0)"), m("pf_hd_b = value_or(pf_world_moved_total, 0)"),
      say("[home lab] Settled so far: <global_val:pf_hd_a>, hunters moved on: <global_val:pf_hd_b>.")]),
    ("PF_HML_burnt", "Friction: the cook burns the soup (now)", "The nearest cook who lives with you burns it; whoever minds most picks a fight.",
     [m("pf_ch_l = 0"), m("pf_ch_av = 1"), m("pf_ch_say = 1"),
      {"u_run_npc_eocs": [{"id": "PF_HML_burn_one", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), m("value_or(u_pf_role, 0) == 1"), m("pf_ch_l == 0")]},
                           "effect": [m("pf_ch_l = 1"), {"run_eocs": "PF_HOME_burnt"}]}], "local": True, "npc_range": 40},
      {"if": m("pf_ch_l == 0"), "then": [say("[home lab] Nobody who lives with you is a cook (change someone's job first).")]}]),
    ("PF_HML_visit", "Neighbors: the nearest settled family comes over now", "Runs the afternoon visit step ignoring the chance and the 5-day wait.  They walk in like any band (on-screen if close).",
     [m("pf_vi_best = 999999"), m("pf_wi = 0"), m("pf_vi_force = 1"),
      {"run_eocs": "PF_WORLD_visit_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
      m("pf_vi_force = 0"),
      {"if": m("pf_vi_best < 999999"), "then": [by_uid(["PF_WORLD_visit_go"], g("pf_vi_lead")), m("pf_vi_tiles = round(pf_vi_best)"), say("[home lab] A family <global_val:pf_vi_tiles> tiles away is on its way.")],
       "else": [say("[home lab] No settled family within 1000 tiles (run 'World: a day of drift' or spawn a settled family).")]}]),
    ("PF_HML_settled", "World: a family settles in a house nearby (30-60 tiles)", "Finds a bed 30-60 tiles away and settles a family there, so you can test visits.",
     [{"u_location_variable": g("pf_ws_at"), "furniture": "f_bed", "target_min_radius": 30, "target_max_radius": 60,
       "true_eocs": [{"id": "PF_HML_settle_here", "effect": [m("pf_ws_kind = 2"), {"run_eocs": "PF_WORLD_spawn_family"}, say("[home lab] A family has made a home in a house nearby.")]}],
       "false_eocs": [{"id": "PF_HML_settle_camp", "effect": [{"u_location_variable": g("pf_ws_at")}, {"location_variable_adjust": g("pf_ws_at"), "x_adjust": 45},
                                                               m("pf_ws_kind = 2"), {"run_eocs": "PF_WORLD_spawn_family"},
                                                               say("[home lab] No bed 30-60 tiles away: a family has made camp 45 tiles east instead.")]}]}]),
    ("PF_HML_horn", "Danger: a zombie appears next to the nearest child (defense test)", "Spawns one zombie beside the nearest child within 30 tiles, so you can watch the adults rally and the child run.",
     [m("pf_hl_d = 99"), {"u_location_variable": g("pf_hl_av")},
      {"u_run_npc_eocs": [{"id": "PF_HML_kid_near", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}]}, "effect": [
          {"u_location_variable": {"u_val": "pf_pos"}},
          {"if": m("distance(u_pf_pos, pf_hl_av) < pf_hl_d"), "then": [m("pf_hl_d = distance(u_pf_pos, pf_hl_av)"), {"u_location_variable": g("pf_hl_kidpos")}]}]}],
       "local": True, "npc_range": 30},
      {"if": m("pf_hl_d < 99"), "then": [{"u_spawn_monster": "mon_zombie", "real_count": 1, "target_var": g("pf_hl_kidpos"), "min_radius": 1, "max_radius": 2},
                                         say("[home lab] A zombie lurches out next to a child.")],
       "else": [say("[home lab] No walking child within 30 tiles.")]}]),
    ("PF_HML_alarm", "Danger: two zombies at the edge of camp (alarm test)", "Spawns two zombies 12 tiles east of you and runs the alarm scan now: watch who raises the alarm, who runs at them, who takes the children away, and the all-clear (wait a few minutes after they're dead).",
     [{"u_location_variable": g("pf_hl_z")}, {"location_variable_adjust": g("pf_hl_z"), "x_adjust": 12},
      {"u_spawn_monster": "mon_zombie", "real_count": 2, "target_var": g("pf_hl_z"), "min_radius": 0, "max_radius": 2},
      m("pf_horn_active = 0"), {"run_eocs": "PF_HORN_tick"}]),
    ("PF_HML_defend_kid", "Danger: a zombie next to the nearest child, Horn off (engine defense test)", "Turns the Horn off for 10 minutes, makes the awake adult nearest to the nearest walking child care about them (warmth 60) and spawns one zombie beside the child.  With the engine build that adult steps in on their own; on the official game they don't.",
     HORN_OFF + [m("pf_hl_d = 99"), {"u_location_variable": g("pf_hl_av")},
      {"u_run_npc_eocs": [{"id": "PF_HML_kid_near3", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}, m("has_var(u_pf_uid)")]}, "effect": [
          {"u_location_variable": {"u_val": "pf_pos"}},
          {"if": m("distance(u_pf_pos, pf_hl_av) < pf_hl_d"), "then": [m("pf_hl_d = distance(u_pf_pos, pf_hl_av)"), {"u_location_variable": g("pf_hl_kidpos")},
                                                                      {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_dg_t")},
                                                                      {"set_string_var": "<u_name>", "target_var": g("pf_dg_tname"), "parse_tags": True}]}]}],
       "local": True, "npc_range": 30},
      {"if": m("pf_hl_d < 99"), "then": [
          {"copy_var": g("pf_hl_kidpos"), "target_var": g("pf_dg_pos")}, {"run_eocs": "PF_HML_protector"},
          {"u_spawn_monster": "mon_zombie", "real_count": 1, "target_var": g("pf_hl_kidpos"), "min_radius": 1, "max_radius": 1},
          say("[home lab] A zombie lurches out next to <global_val:pf_dg_tname>.")],
       "else": [say("[home lab] No walking child within 30 tiles.")]}]),
    ("PF_HML_defend_you", "Danger: a zombie next to you, Horn off (engine defense test)", "Turns the Horn off for 10 minutes, makes the awake adult nearest to you care about you (warmth 60) and spawns one zombie 2 tiles from you.  With the engine build they step in; everyone else who already cares enough about you should too (see the next entry).",
     HORN_OFF + [{"set_string_var": "AVATAR", "target_var": g("pf_dg_t")}, {"set_string_var": "you", "target_var": g("pf_dg_tname")},
      {"u_location_variable": g("pf_hl_av")},
      {"copy_var": g("pf_hl_av"), "target_var": g("pf_dg_pos")}, {"run_eocs": "PF_HML_protector"},
      {"u_spawn_monster": "mon_zombie", "real_count": 1, "min_radius": 2, "max_radius": 2},
      say("[home lab] A zombie lurches out right next to you.")]),
    ("PF_HML_defend_who", "Defense: who would stand up for you (engine rules)", "Lists everyone within 30 tiles who counts as bonded to you under the engine's rules: kin, partner, household, or warmth 40+ (pf_defend_w).",
     [{"set_string_var": "AVATAR", "target_var": g("pf_dg_t")}, m("pf_dg_n = 0"),
      {"u_run_npc_eocs": ["PF_HML_who_one"], "local": True, "npc_range": 30},
      say("[home lab] <global_val:pf_dg_n> people would stand up for you.")]),
    ("PF_HML_defend_range", "Defense: range test (trace on, Horn off, you 20 tiles out, zombie next to you)", "One-press version of the engine defense test: turns the trace on and the Horn off, moves you about 20 tiles south-west of where you stand (away from the camp) and spawns a zombie next to you.  Bonded people should come; others shouldn't.  Read config/debug.log ('PF defend').",
     HORN_OFF + [m("pf_debug_defend = 1"),
      {"u_location_variable": g("pf_hl_far")}, {"location_variable_adjust": g("pf_hl_far"), "x_adjust": -14, "y_adjust": 14},
      {"u_teleport": g("pf_hl_far"), "force_safe": True},
      {"u_spawn_monster": "mon_zombie", "real_count": 1, "min_radius": 2, "max_radius": 2},
      say("[home lab] Trace on.  You're out in the open, and a zombie lurches out next to you.")]),
    ("PF_HML_defend_trace", "Defense: trace combat decisions to debug.log (on/off, engine build)", "Toggles the engine's decision trace: every turn, each of our people's friends, hostiles, target and action are written to config/debug.log (lines starting 'PF defend').  For testing only.",
     [m("pf_debug_defend = 1 - value_or(pf_debug_defend, 0)"),
      {"if": m("pf_debug_defend == 1"), "then": [say("[home lab] Defense trace on (config/debug.log, 'PF defend').")], "else": [say("[home lab] Defense trace off.")]}]),
    # 2026-10-16 (the user: "force test patch 22 and patch 18")
    ("PF_HML_t22", "Test: patch 22, a resident walks to you across deep water (trace on, Horn off)", "Stand in open ground.  Digs a strip of deep water 2 wide and 17 long 3 tiles east of you, puts the nearest grown-up who lives here 1 tile east of you and orders them to a spot 7 tiles east (across the strip).  With patch 22 they walk round the end; read config/debug.log ('PF path': deep_water=0).  Ruins the ground: use a copy of the world.",
     HORN_OFF + [m("pf_debug_defend = 1"), m("pf_t22_ok = 0"), {"u_location_variable": g("pf_t22_av")}]
     + [e for dx in (3, 4) for dy in range(-8, 9) for e in (
         {"copy_var": g("pf_t22_av"), "target_var": g("pf_t22_w")},
         {"location_variable_adjust": g("pf_t22_w"), "x_adjust": dx, "y_adjust": dy},
         {"u_transform_radius": 0, "ter_furn_transform": "PF_LAB_t_deepwater", "target_var": g("pf_t22_w")})]
     + [{"copy_var": g("pf_t22_av"), "target_var": g("pf_t22_from")}, {"location_variable_adjust": g("pf_t22_from"), "x_adjust": 1},
        {"copy_var": g("pf_t22_av"), "target_var": g("pf_t22_to")}, {"location_variable_adjust": g("pf_t22_to"), "x_adjust": 7},
        m("pf_t22_d = 99"),
        {"u_run_npc_eocs": [{"id": "PF_HML_t22_pick", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), {"not": {"u_has_effect": "sleep"}}]}, "effect": [
            {"u_location_variable": {"u_val": "pf_pos"}},
            {"if": m("distance(u_pf_pos, pf_t22_av) < pf_t22_d"), "then": [m("pf_t22_d = distance(u_pf_pos, pf_t22_av)"), {"u_set_talker": g("pf_t22_who")}]}]}],
         "local": True, "npc_range": 30},
        {"if": m("pf_t22_d < 99"), "then": [
            {"run_eocs": {"id": "PF_HML_t22_go", "effect": [
                {"u_teleport": g("pf_t22_from"), "force_safe": True},
                {"copy_var": g("pf_t22_to"), "target_var": {"u_val": "pf_walk_to"}},
                {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
                {"set_string_var": "<u_name>", "target_var": g("pf_t22_name"), "parse_tags": True}]}, "alpha_talker": g("pf_t22_who")},
            say("[home lab] Deep water dug.  <global_val:pf_t22_name> is beside you, told to walk to the far side.  Wait a minute and watch.")],
         "else": [say("[home lab] Nobody who lives here is within 30 tiles.")]}]),
    ("PF_HML_t18", "Test: patch 18, one of your children alone 8 tiles east of you, zombies to the north (trace on, Horn off)", "Go 3 map squares from home first (a child only panics with no grown-up in sight).  Brings the first of your walking children (by unique id, from anywhere) 8 tiles east of you and spawns four zombies 3 tiles north of them.  Vanilla flight would go south; with patch 18 the child runs west to you.  Read config/debug.log ('PF flee').  Use a copy of the world.",
     HORN_OFF + [m("pf_debug_defend = 1"), m("pf_t18_found = 0"), m("pf_t18_k = 0"), {"u_location_variable": g("pf_hl_av")},
      {"copy_var": g("pf_hl_av"), "target_var": g("pf_t18_at")}, {"location_variable_adjust": g("pf_t18_at"), "x_adjust": 8},
      {"run_eocs": {"id": "PF_HML_t18_k", "effect": [
          {"set_string_var": "pf_kid_<global_val:pf_t18_k>", "target_var": ctx("kr"), "parse_tags": True},
          {"copy_var": {"var_val": "kr"}, "target_var": g("pf_t18_uid")},
          {"set_string_var": "pf_reg_<global_val:pf_t18_uid>_dead", "target_var": ctx("kd"), "parse_tags": True},
          {"if": {"and": [m("value_or(v_kd, 0) == 0"), m("has_var(v_kr)"), {"not": {"compare_string": [g("pf_t18_uid"), "none"]}}]}, "then": [
              {"u_run_npc_eocs": [{"id": "PF_HML_t18_go", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}, m("pf_t18_found == 0")]}, "effect": [
                  m("pf_t18_found = 1"), {"u_teleport": g("pf_t18_at"), "force_safe": True},
                  {"set_string_var": "<u_name>", "target_var": g("pf_dg_tname"), "parse_tags": True}]}],
               "unique_ids": [g("pf_t18_uid")], "local": False}]},
          m("pf_t18_k += 1")]}, "condition": m("(pf_t18_k < 30) * (pf_t18_found == 0)"), "iterations": 30},
      {"if": m("pf_t18_found == 1"), "then": [
          {"copy_var": g("pf_t18_at"), "target_var": g("pf_t18_kid")}, {"location_variable_adjust": g("pf_t18_kid"), "y_adjust": -3},
          {"u_spawn_monster": "mon_zombie", "real_count": 4, "target_var": g("pf_t18_kid"), "min_radius": 0, "max_radius": 1},
          say("[home lab] <global_val:pf_dg_tname> is 8 tiles east of you, four zombies just north of them.")],
       "else": [say("[home lab] None of your children can walk yet.")]}]),
    ("PF_HML_day", "Daytime: two people near you do something now (variety pass)", "Runs the daytime pass now, whatever the hour: two adults within 25 tiles each do something small, alone or with someone.",
     [m("pf_day_n = 0"), m("pf_day_force = 1"), {"u_run_npc_eocs": ["PF_DAY_one"], "local": True, "npc_range": 25}, m("pf_day_force = 0")]),
    ("PF_HML_bedroll", "Night: people without a bed lie down to sleep now", "Runs the night's bedroll pass now, whatever the hour: our people without a bed at home (not the watcher) sleep about five hours where they are.",
     [m("pf_bedroll_night = -1"), {"run_eocs": "PF_NIGHT_bedroll"},
      {"if": m("pf_threat > 0"), "then": [say("[home lab] Something hostile is in sight, so nobody lies down.")],
       "else": [say("[home lab] <global_val:pf_bedroll_n> people lie down to sleep.")]}]),
    ("PF_HML_rk_tend", "Reckoning: tend the wounded now", "Runs the tending pass now instead of waiting for the 3-minute tick: if nothing hostile is around, up to three wounded people are cleaned up and wrapped by a carer or the nearest adult.",
     [m("pf_rk_need = 1"), {"run_eocs": "PF_RK_tick"}]),
    ("PF_HML_rk_retell", "Reckoning: tonight's retelling now", "Runs the fire's retelling of today's rescue or storm now (once per day normally).",
     [{"if": {"or": [m(f"value_or(pf_rk_day, -1) == {TODAY}"), m(f"value_or(pf_rk_storm_day, -1) == {TODAY}")]},
       "then": [m("pf_rk_told_day = -1"), {"run_eocs": "PF_RK_retell"}],
       "else": [say("[home lab] Nobody was saved and no storm passed today, so there's nothing to retell.")]}]),
    ("PF_HML_rk_nightmare", "Reckoning: a nightmare now (someone frightened or mourning)", "Runs tonight's nightmare check now, whatever the hour, and makes it happen if anyone near you was frightened in the last day or is mourning.",
     [m("pf_nm_force = 1"), m("pf_nm_night = -1"), {"run_eocs": "PF_RK_nm_try"}, m("pf_nm_force = 0"),
      {"if": m("pf_nm_best < 0"), "then": [say("[home lab] Nobody near you was frightened in the last day or is mourning.")]}]),
    ("PF_HML_rk_nightmare_adult", "Reckoning: a grown-up's nightmare now", "As above, but only grown-ups can have it (children always win the draw): the adult comforter's line, or crying it out alone.",
     [m("pf_nm_force = 1"), m("pf_nm_adult_only = 1"), m("pf_nm_night = -1"), {"run_eocs": "PF_RK_nm_try"}, m("pf_nm_force = 0"), m("pf_nm_adult_only = 0"),
      {"if": m("pf_nm_best < 0"), "then": [say("[home lab] No grown-up near you was frightened in the last day or is mourning.")]}]),
    ("PF_HML_rk_storm", "Reckoning: a portal storm begins and ends (simulated)", "Runs the storm's start, then its end, as if a portal storm had just passed over (real storms are noticed every 5 minutes).",
     [{"run_eocs": "PF_RK_storm_start"}, {"run_eocs": "PF_RK_storm_end"}]),
    ("PF_HML_rk_stats", "Reckoning: stats", "Rescues and tending so far.",
     [m("pf_hs_a = value_or(pf_rescues_total, 0)"), m("pf_hs_b = value_or(pf_tended_total, 0)"),
      m("pf_hs_c = value_or(pf_ran_total, 0)"), m("pf_hs_d = value_or(pf_nightmares_total, 0)"), m("pf_hs_e = value_or(pf_storms_total, 0)"),
      say("[home lab] rescues <global_val:pf_hs_a>, wounded tended <global_val:pf_hs_b>, people who ran <global_val:pf_hs_c>, nightmares <global_val:pf_hs_d>, storms lived through <global_val:pf_hs_e>.")]),
    ("PF_HML_rk_pack", "Danger: a pack of six zombies 8 tiles east, Horn off (who breaks and runs?)", "Turns the Horn off for 10 minutes and spawns six zombies 8 tiles east of you.  Big enough that some people should panic and run; with the engine build that is recorded (pf_fled_t) and judged once it's calm.  Expect casualties; kill the game without saving afterwards.",
     HORN_OFF + [{"u_location_variable": g("pf_hl_z")}, {"location_variable_adjust": g("pf_hl_z"), "x_adjust": 8},
      {"u_spawn_monster": "mon_zombie", "real_count": 6, "target_var": g("pf_hl_z"), "min_radius": 0, "max_radius": 2},
      say("[home lab] Six zombies shamble in from the east.")]),
    ("PF_HML_rk_ran","Reckoning: the nearest adult 'ran' from the last fight (engine stamp, for testing)", "Marks the awake adult nearest to you as having broken and run a minute ago (what the engine build records when someone flees), then runs the calm-time pass.  If you or someone near was hurt in the last 15 minutes, they're judged for it.",
     [m("pf_hl_d = 99"), {"u_location_variable": g("pf_hl_av")},
      {"u_run_npc_eocs": [{"id": "PF_HML_ran_near", "condition": {"and": [ADULT, m("has_var(u_pf_uid)"), {"not": {"u_has_flag": "CANNOT_ATTACK"}}]}, "effect": [
          {"u_location_variable": {"u_val": "pf_pos"}},
          {"if": m("distance(u_pf_pos, pf_hl_av) < pf_hl_d"), "then": [m("pf_hl_d = distance(u_pf_pos, pf_hl_av)"), {"u_set_talker": g("pf_hl_ran")}]}]}],
       "local": True, "npc_range": 20},
      {"if": m("pf_hl_d < 99"), "then": [
          {"run_eocs": [{"id": "PF_HML_ran_mark", "effect": [m("u_pf_fled_t = time('now') - time('1 m')"), m("u_pf_hurt_t = -1")]}], "alpha_talker": g("pf_hl_ran")},
          m("pf_rk_need = 1"), {"run_eocs": "PF_RK_tick"}],
       "else": [say("[home lab] No adult within 20 tiles.")]}]),
    ("PF_HML_tl_animals", "Town: the neighbors' animals arrive now", "Hens, a goat or a cow arrive at home (friendly, permanent).  Needs a home.", [{"run_eocs": "PF_TL_animals"}]),
    ("PF_HML_tl_morning", "Town: this morning's milk, eggs and field step now", "The herder brings in the milk and eggs; a fallow field in season is planted, a grown one harvested.", [{"run_eocs": "PF_TL_morning"}]),
    ("PF_HML_tl_grow", "Town: the planted field is grown", "Moves the planted field's clock on, so the next morning step harvests it.", [{"run_eocs": "PF_TL_grow"}]),
    ("PF_HML_tl_feast", "Town: tonight's harvest feast, now", "The harvest feast (normally the evening of a harvest day).", [{"run_eocs": "PF_TL_feast"}]),
    ("PF_HML_tl_job", "Town: the nearest resident takes the next job", "Cycles the job of the resident nearest you (cook, guard, forager, tinkerer, carer, herder, farmer, smith, healer, teacher) and says which.",
     [m("pf_hl_d = 99"), {"u_location_variable": g("pf_hl_av")},
      {"u_run_npc_eocs": [{"id": "PF_HML_job_near", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1")]}, "effect": [
          {"u_location_variable": {"u_val": "pf_pos"}},
          {"if": m("distance(u_pf_pos, pf_hl_av) < pf_hl_d"), "then": [m("pf_hl_d = distance(u_pf_pos, pf_hl_av)"), {"u_set_talker": g("pf_hl_res")}]}]}],
       "local": True, "npc_range": 40},
      {"if": m("pf_hl_d < 99"), "then": [{"run_eocs": "PF_HOME_role_next", "beta_talker": g("pf_hl_res")}], "else": [say("[home lab] Nobody who lives with you is near.")]}]),
    ("PF_HML_tl_workday", "Town: today's school, healer's round and smithy now", "Runs the working day now: the teacher's school, the healer's round and the smith's work (needs people with those jobs).", [{"run_eocs": "PF_TL_workday"}]),
    ("PF_HML_tl_market", "Town: market day now (+30 stores)", "Adds 30 stores and holds market day: up to 3 goods at home.", [{"run_eocs": "PF_TL_market"}]),
    ("PF_HML_tl_stats2", "Town: work stats", "School days, people treated, smithy work, markets and stores.", [{"run_eocs": "PF_TL_stats2"}]),
    ("PF_HML_tl_join", "Town: the nearest settled family decides to join now", "Picks the nearest settled family (ignoring visits and draw) and sends it to your place.  They ask (a yes/no popup) once they're within 25 tiles of home and it's calm.", [{"run_eocs": "PF_TL_join"}]),
    ("PF_HML_tl_join_ask", "Town: the family on its way asks now", "Skips the walk: the family on its way asks right away, wherever they are.", [{"run_eocs": "PF_TL_join_ask"}]),
    ("PF_HML_tl_watch", "Town: tonight's watch goes up now", "Picks tonight's rota and sends the first shift to their posts (needs 3+ grown-ups who live here, within 60 tiles).", [{"run_eocs": "PF_TL_watch"}]),
    ("PF_HML_tl_watch_change", "Town: change of watch now", "The first shift goes to bed, the second is woken and goes out.", [{"run_eocs": "PF_TL_watch_change"}]),
    ("PF_HML_tl_watch_dawn", "Town: the watch comes in now", "Dawn: the watch comes in (shared moments, the morning line).", [{"run_eocs": "PF_TL_watch_dawn"}]),
    ("PF_HML_tl_watch_spot", "Town: a zombie near someone on the watch", "Spawns a zombie 7 tiles east of a watcher on a post: they should see it and raise the Horn by name.", [{"run_eocs": "PF_TL_watch_spot"}]),
    ("PF_HML_tl_bring", "Town: the newest household comes to its house (repair)", "Places the family that joined last at its house (for a family that joined out of range).", [{"run_eocs": "PF_TL_bring"}]),
    ("PF_HML_tl_stats3", "Town: town stats (households, watch)", "Households, families joined, nights watched, sightings, the place's draw and tonight's watch phase.", [{"run_eocs": "PF_TL_stats3"}]),
    ("PF_HML_kl_meet", "Keep: the meeting sits now", "The weekly meeting, now: a vote if there's no chief (or the town has turned on them), else the worst quarrel for the chief to settle.  Skips the call and the 4-adult rule (needs 2).", [{"run_eocs": "PF_KL_meet"}]),
    ("PF_HML_kl_fallout", "Keep: the two nearest grown-ups have a row", "Two arguments at full strength between the two residents nearest you (within 30 tiles, not the chief): a quarrel for the next meeting.", [{"run_eocs": "PF_KL_fallout"}]),
    ("PF_HML_kl_dissent", "Keep: everyone turns on the chief", "Everyone who lives here feels betrayed by the chief: the next meeting holds a vote of confidence.", [{"run_eocs": "PF_KL_dissent"}]),
    ("PF_HML_kl_vacant", "Keep: the chair is empty", "No chief; a meeting is due the next evening.", [{"run_eocs": "PF_KL_vacant"}]),
    ("PF_HML_kl_law", "Keep: somebody puts a law to the vote now", "A random law (not in force; or one in force, to do away with) is proposed by someone it suits and voted on now, you included.", [{"run_eocs": "PF_KL_law"}]),
    ("PF_HML_kl_shirk", "Keep: the tithe, and the nearest resident keeps theirs back", "Makes the tithe law, adds 4 to this week's tithe, and has the resident nearest you keep their share back: it comes up at the next meeting.", [{"run_eocs": "PF_KL_shirk"}]),
    ("PF_HML_kl_rest", "Keep: the rest day's morning now", "Morale and a quiet time with everyone who lives here (as on the rest day).", [{"run_eocs": "PF_KL_rest"}]),
    ("PF_HML_kl_laws", "Keep: the laws (stats)", "Which laws are in force, and how the votes went.", [{"run_eocs": "PF_KL_laws"}]),
    ("PF_HML_kl_lord", "Keep: the chief becomes lord for life", "Puts the lord law in force (needs a chief): no more elections while they live, their word over the meeting's, a coup only at two-thirds, and an heir after them.", [{"run_eocs": "PF_KL_lord"}]),
    ("PF_HML_kl_succeed", "Keep: the lord names an heir and hands over", "The lord (if here) names an heir, then the heir takes the chair as if the lord had died (nobody dies).", [{"run_eocs": "PF_KL_succeed"}]),
    ("PF_HML_kl_outcast", "Keep: everyone turns on the nearest resident", "Everyone who lives here feels betrayed by the resident nearest you (not the chief): the next meeting votes on putting them out.", [{"run_eocs": "PF_KL_outcast"}]),
    ("PF_HML_kl_rule", "Keep: who rules (stats)", "The lord law, the heir, successions, coups and exiles.", [{"run_eocs": "PF_KL_rule"}]),
    ("PF_HML_kl_wall", "Keep: the next side of the wall goes up now", "Starts the wall if there isn't one, and builds the next side now (north, east, south, west; a gate in each).", [{"run_eocs": "PF_KL_wall_side"}]),
    ("PF_HML_kl_wall_redo", "Keep: rebuild the side of the wall nearest you", "The nearest side goes up again (where it's open ground); anyone standing on the line steps off first: stand on a gate to test it.", [{"run_eocs": "PF_KL_wall_redo"}]),
    ("PF_HML_kl_siege_warn", "Keep: a horde is coming tonight", "Word comes now, and the siege is tonight (from 21:00; three waves 40 minutes apart while you're home).", [{"run_eocs": "PF_KL_siege_warn"}]),
    ("PF_HML_kl_siege_wave", "Keep: the next wave now", "Spawns the next wave of the coming siege now (35 tiles out in the warned direction).", [{"run_eocs": "PF_KL_siege_wave"}]),
    ("PF_HML_kl_siege_end", "Keep: the siege is over (tally now)", "The tally, the morale and the bond, now.", [{"run_eocs": "PF_KL_siege_end"}]),
    ("PF_HML_kl_walls", "Keep: walls and sieges (stats)", "The wall and the siege state.", [{"run_eocs": "PF_KL_walls"}]),
    ("PF_HML_kl_nb_contact", "Neighbors: a new settlement takes notice now", "A keep, the eyeglasses or the woodlanders (in turn), up to three.", [{"run_eocs": "PF_KL_nb_contact"}]),
    ("PF_HML_kl_nb_envoy", "Neighbors: the next envoy now", "The next settlement in turn sends an envoy (an offer, a demand, or a courtesy visit, by how things stand).", [{"run_eocs": "PF_KL_nb_envoy"}]),
    ("PF_HML_kl_nb_week", "Neighbors: a week of agreements now", "Deliveries, tribute, and hostile ones start arming.", [{"run_eocs": "PF_KL_nb_week"}]),
    ("PF_HML_kl_nb_raid", "Neighbors: the first settlement raids now", "Strength against defense (wall, watch, people, an ally).", [{"run_eocs": "PF_KL_nb_raid"}]),
    ("PF_HML_kl_nb_raid_win", "Neighbors: the first settlement raids and gets through", "The losing raid: they take stores (topped up to 12 first) and, with you home, a resident outside is hurt.", [{"run_eocs": "PF_KL_nb_raid_win"}]),
    ("PF_HML_kl_nb_sour", "Neighbors: the first settlement turns hostile", "Relation -40: they arm at the next week's upkeep.", [{"run_eocs": "PF_KL_nb_sour"}]),
    ("PF_HML_kl_nb_warm", "Neighbors: the first settlement turns friendly", "Relation 50: their next envoy proposes a pact.", [{"run_eocs": "PF_KL_nb_warm"}]),
    ("PF_HML_kl_stats", "Keep: stats", "Meetings, elections, quarrels, confidence votes and the chief.", [{"run_eocs": "PF_KL_stats"}]),
    ("PF_HML_kl_council", "Council: a council of three becomes law", "No lord any more; the next meeting (or the next row) chooses the council.", [{"run_eocs": "PF_KL_council"}]),
    ("PF_HML_kl_cn_elect", "Council: the council is chosen now", "You're asked whether you stand; everyone votes; the three with the most hands sit, and the first speaks for it.", [{"run_eocs": "PF_KL_cn_elect"}]),
    ("PF_HML_kl_cn_door", "Council: a family at the door, for the council (dry run)", "Each councillor here says yes or no (you too, if you hold a seat); nobody actually moves in.", [{"run_eocs": "PF_KL_cn_door"}]),
    ("PF_HML_kl_cn_stats", "Council: who sits (stats)", "The seats, who speaks for it, who is here, and how often it has ruled.", [{"run_eocs": "PF_KL_cn_stats"}]),
    ("PF_HML_kl_nb_match", "Neighbors: the first settlement will offer a match", "Makes it close and agreed with you; the next envoy (t) offers one of theirs to marry a single grown-up here.", [{"run_eocs": "PF_KL_nb_match"}]),
    ("PF_HML_kl_nb_agree", "Neighbors: a match is agreed now (the nearest free resident)", "Skips the envoy and the offer: the nearest grown-up without a partner who lives here is promised to the first settlement's match.", [{"run_eocs": "PF_KL_nb_agree"}]),
    ("PF_HML_kl_nb_wed", "Neighbors: the one from the other place arrives now", "If a match is agreed: they walk in, move in, and are engaged (the wedding is at the evening fire).", [{"run_eocs": "PF_KL_nb_wed"}]),
    ("PF_HML_kl_nv_door", "Neighbors: the walking envoy is at the door now", "Skips the walk: the envoy steps to the door and speaks within the minute.", [{"run_eocs": "PF_KL_nv_door"}]),    ("PF_HML_kl_acquaint", "Keep: everyone who lives here gets to know each other", "Shared danger between every pair of grown-ups who live here, and with you, so votes have someone to go to.", [{"run_eocs": "PF_KL_acquaint"}]),
    ("PF_HML_tl_stats", "Town: stats", "Milk, eggs, plantings, harvests and animal gifts so far.", [{"run_eocs": "PF_TL_stats"}]),
    ("PF_HML_name_kid", "Naming: rename the nearest child, as if you took them in (engine build)", "Runs the adoption naming prompt on the nearest walking child within 10 tiles.  Needs the People First engine build and the People First: Engine mod (on a stock build nothing happens).",
     [m("pf_hl_d = 99"), {"u_location_variable": g("pf_hl_av")},
      {"u_run_npc_eocs": [{"id": "PF_HML_kid_near2", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}]}, "effect": [
          {"u_location_variable": {"u_val": "pf_pos"}},
          {"if": m("distance(u_pf_pos, pf_hl_av) < pf_hl_d"), "then": [m("pf_hl_d = distance(u_pf_pos, pf_hl_av)"), {"u_set_talker": g("pf_hl_kid")}]}]}],
       "local": True, "npc_range": 10},
      {"if": m("pf_hl_d < 99"), "then": [{"run_eocs": "PF_ENGINE_name_adoptee", "beta_talker": g("pf_hl_kid")}], "else": [say("[home lab] No walking child within 10 tiles.")]}]),
    ("PF_HML_name_baby", "Naming: name the nearest baby as if it were yours (engine build)", "Runs the newborn naming prompt on the nearest baby within 10 tiles, as if you were its mother.  Needs the engine build.",
     [m("pf_hl_d = 99"), {"u_location_variable": g("pf_hl_av")},
      {"u_run_npc_eocs": [{"id": "PF_HML_baby_near", "condition": {"u_has_effect": "PF_infant"}, "effect": [
          {"u_location_variable": {"u_val": "pf_pos"}},
          {"if": m("distance(u_pf_pos, pf_hl_av) < pf_hl_d"), "then": [m("pf_hl_d = distance(u_pf_pos, pf_hl_av)"), {"u_set_talker": g("pf_hl_kid")}]}]}],
       "local": True, "npc_range": 10},
      {"if": m("pf_hl_d < 99"), "then": [{"copy_var": g("pf_fm_mom"), "target_var": g("pf_hl_mom_was")}, {"set_string_var": "AVATAR", "target_var": g("pf_fm_mom")},
                                         {"run_eocs": "PF_ENGINE_name_baby", "alpha_talker": g("pf_hl_kid")},
                                         {"copy_var": g("pf_hl_mom_was"), "target_var": g("pf_fm_mom")}],
       "else": [say("[home lab] No baby within 10 tiles.")]}]),
    ("PF_HML_wake", "Morning: someone makes you breakfast now", "Runs the wake-up signal as if you just woke at home (it still needs someone who cares, and a home within 30 tiles).",
     [m("pf_bk_day = -1"), {"run_eocs": "PF_HOME_wake_lab"}]),
    ("PF_HML_trust", "Bands: the nearest band member warms to you (warmth 50, trust 40)", "So you can ask them to come live with you.",
     [m("pf_hl_d = 99"), {"u_location_variable": g("pf_hl_av")},
      {"u_run_npc_eocs": [{"id": "PF_HML_near", "condition": {"and": [ADULT, m("value_or(u_pf_is_leader, -1) >= 0")]}, "effect": [
          {"u_location_variable": {"u_val": "pf_pos"}},
          {"if": m("distance(u_pf_pos, pf_hl_av) < pf_hl_d"), "then": [m("pf_hl_d = distance(u_pf_pos, pf_hl_av)"), {"u_set_talker": g("pf_hl_who")}]}]}],
       "local": True, "npc_range": 30},
      {"if": m("pf_hl_d < 99"), "then": [{"run_eocs": "PF_HML_warm", "alpha_talker": g("pf_hl_who")}, say("[home lab] <global_val:pf_say_a> likes you now.")],
       "else": [say("[home lab] No band member within 30 tiles.")]}]),
    ("PF_HML_spawn", "World: a band appears now (hunters, family, or settled family)", "Runs the natural spawn once, ignoring the population cap.  Kinds: 0 hunters, 1 family on the move, 2 settled family.",
     [{"run_eocs": "PF_WORLD_spawn"}, say("[home lab] Spawned kind <global_val:pf_ws_kind> at the edge of the bubble.")]),
    ("PF_HML_family_here", "World: a family appears right here", "A family on the move, a few tiles away, so you can watch them.",
     [{"u_location_variable": g("pf_ws_at")}, {"location_variable_adjust": g("pf_ws_at"), "x_adjust": 6}, m("pf_ws_kind = 1"),
      {"run_eocs": "PF_WORLD_spawn_family"}, say("[home lab] A family walks up.")]),
    ("PF_HML_stats", "Stats: home and world", "Home evenings, people living with you, bands that joined you, bands alive, natural spawns.",
     [m("pf_wl = 0"), m("pf_wi = 0"), {"run_eocs": "PF_WORLD_count_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
      m("pf_hs_a = value_or(pf_home_evenings_total, 0)"), m("pf_hs_b = value_or(pf_residents_n, 0)"), m("pf_hs_c = value_or(pf_bands_joined_total, 0)"),
      m("pf_hs_d = value_or(pf_world_spawned_total, 0)"), m("pf_hs_e = value_or(pf_set_bands, 8)"),
      m("pf_hs_f = value_or(pf_chores_total, 0)"), m("pf_hs_g = value_or(pf_burnt_total, 0)"), m("pf_hs_h = value_or(pf_visits_total, 0)"), m("pf_hs_i = value_or(pf_residents_left_total, 0)"),
      say("[home] evenings at home <global_val:pf_hs_a>, residents <global_val:pf_hs_b>, bands joined <global_val:pf_hs_c> | world: bands alive <global_val:pf_wl> of <global_val:pf_hs_e>, natural spawns <global_val:pf_hs_d> | chores <global_val:pf_hs_f>, burnt soups <global_val:pf_hs_g>, visits <global_val:pf_hs_h>, residents who left <global_val:pf_hs_i>.")]),
]
lab = [eoc(i, e, d) for i, n, d, e in HL]
lab.append(eoc("PF_HML_warm", [name_into("pf_say_a"), {"run_eocs": "PF_ID_ensure"},
                               m("u_pf_v_AVATAR_w = max(value_or(u_pf_v_AVATAR_w, 0), 50)"), m("u_pf_v_AVATAR_t = max(value_or(u_pf_v_AVATAR_t, 0), 40)"),
                               m("u_pf_v_AVATAR_pw = max(value_or(u_pf_v_AVATAR_pw, 0), 50)"), m("u_pf_v_AVATAR_pt = max(value_or(u_pf_v_AVATAR_pt, 0), 40)"),
                               m("u_pf_v_AVATAR_l = time('now')")],
                 "u = the band member.  Their view of you (u_pf_v_AVATAR_*) jumps to warmth 50, trust 40 (peaks too, so lazy decay doesn't undo it)."))
_tosay_n = [0]
def tosay(text):
    """A player-facing line from inside an NPC's EOC (an NPC's u_message isn't shown)."""
    _tosay_n[0] += 1
    return {"run_eocs": [{"id": "PF_HML_say_%d" % _tosay_n[0], "effect": [say(text)]}], "alpha_talker": "avatar"}
lab.append(eoc("PF_HML_horn_back", [m("pf_horn_on = 1"), say("[home lab] The Horn is back on.")]))
lab.append(eoc("PF_HML_protector", [
    m("pf_dg_best = 99"),
    {"u_run_npc_eocs": [{"id": "PF_HML_prot_cand", "condition": {"and": [ADULT, m("has_var(u_pf_uid)"), {"not": {"u_has_effect": "sleep"}}, {"not": {"u_has_flag": "CANNOT_ATTACK"}},
                                                                      {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_dg_t")]}}]}, "effect": [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_dg_pos) < pf_dg_best"), "then": [m("pf_dg_best = distance(u_pf_pos, pf_dg_pos)"), {"u_set_talker": g("pf_dg_prot")}]}]}],
     "local": True, "npc_range": 40},
    {"if": m("pf_dg_best <= 20"), "then": [
        {"run_eocs": [{"id": "PF_HML_prot_set", "effect": [
            {"set_string_var": "u_pf_v_<global_val:pf_dg_t>_w", "target_var": ctx("rw"), "parse_tags": True},
            {"set_string_var": "u_pf_v_<global_val:pf_dg_t>_pw", "target_var": ctx("rpw"), "parse_tags": True},
            m("v_rw = max(value_or(v_rw, 0), 60)"), m("v_rpw = max(value_or(v_rpw, 0), 60)"),
            {"set_string_var": "<u_name>", "target_var": g("pf_dg_pname"), "parse_tags": True}]}], "alpha_talker": g("pf_dg_prot")},
        say("[home lab] <global_val:pf_dg_pname> cares about <global_val:pf_dg_tname> now (warmth 60), <global_val:pf_dg_best> tiles away.")],
     "else": [say("[home lab] No awake adult within 20 tiles to care about <global_val:pf_dg_tname>.")]},
], "u = avatar.  pf_dg_t = the uid to protect (AVATAR for you), pf_dg_pos = where they are.  The awake adult nearest to them gets warmth 60 toward them (a bond under the engine's rules)."))
lab.append(eoc("PF_HML_who_one", [
    {"set_string_var": "u_pf_v_<global_val:pf_dg_t>_w", "target_var": ctx("rw"), "parse_tags": True},
    {"set_string_var": "", "target_var": g("pf_dg_why")},
    {"if": {"or": [{"compare_string": [{"u_val": "pf_mom"}, g("pf_dg_t")]}, {"compare_string": [{"u_val": "pf_dad"}, g("pf_dg_t")]}, {"compare_string": [{"u_val": "pf_guardian"}, g("pf_dg_t")]}]},
     "then": [{"set_string_var": "family", "target_var": g("pf_dg_why")}]},
    {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"u_val": "pf_sweet"}, g("pf_dg_t")]}]}, "then": [{"set_string_var": "partner", "target_var": g("pf_dg_why")}]},
    {"if": m("value_or(u_pf_resident, 0) == 1"), "then": [{"set_string_var": "lives with you", "target_var": g("pf_dg_why")}]},
    {"if": m("value_or(v_rw, 0) >= value_or(pf_defend_w, 40)"), "then": [m("pf_dg_w = value_or(v_rw, 0)"), {"set_string_var": "warmth <global_val:pf_dg_w>", "target_var": g("pf_dg_why"), "parse_tags": True}]},
    {"if": {"not": {"compare_string": [g("pf_dg_why"), ""]}}, "then": [
        m("pf_dg_n += 1"), {"set_string_var": "<u_name>", "target_var": g("pf_dg_pname"), "parse_tags": True},
        {"if": {"u_has_effect": "sleep"}, "then": [{"set_string_var": "<global_val:pf_dg_why> (asleep)", "target_var": g("pf_dg_why"), "parse_tags": True}]},
        tosay("[home lab] <global_val:pf_dg_pname>: <global_val:pf_dg_why>")]},
], "u = an NPC.  Says whether they count as bonded to pf_dg_t under the engine's rules (pf_protects in engine/apply_patches.py; band membership isn't checked for you).",
    condition={"and": [m("has_var(u_pf_uid)"), {"not": {"u_has_flag": "CANNOT_ATTACK"}}]}))
lab.append(eoc("PF_HOME_wake_lab", [
    {"u_location_variable": g("pf_hm_av")},
    {"if": {"and": [m(AT_HOME), m("distance(pf_hm_av, pf_home_loc) <= 30")]},
     "then": [m("pf_bk_day = %s" % TODAY), m("pf_hm_best = -1"),
              {"u_run_npc_eocs": ["PF_HOME_cook_cand"], "local": True, "npc_range": 20},
              {"if": m("pf_hm_best >= 0"), "then": [{"run_eocs": "PF_HOME_cook", "alpha_talker": g("pf_hm_cook"), "beta_talker": "avatar"}],
               "else": [say("[home lab] Nobody here cares enough to cook for you (warmth 20+).")]}],
     "else": [say("[home lab] You're not home (set one in Home, and be within 30 tiles).")]},
]))
# The Keep's rows get a lab of their own (the Home lab ran out of keys at 62): one row here opens it.
KLR = [r for r in HL if r[0].startswith("PF_HML_kl_")]
HLM = [r for r in HL if not r[0].startswith("PF_HML_kl_")]
HLM.append(("PF_HML_keep_lab", "Keep lab (v0.6): meetings, chiefs, laws, who rules", "Opens the Keep lab: the meeting now, quarrels, dissent, laws, the tithe, the rest day, a lord and heir, exile, stats.",
            [{"run_eocs": "PF_HML_keep_open"}]))
lab.append(eoc("PF_HML_keep_lab", [{"run_eocs": "PF_HML_keep_open"}]))
HLM.append(("PF_HML_away_lab", "Open threads lab (v0.7): while you're away, the road, loss, the tense evening", "Opens the v0.7 lab: the household roll, leaving, days passing at home, raids while you're gone, coming home, trouble for a band on the road, a child losing a parent, the tense evening.",
            [{"run_eocs": "PF_AWL_open"}]))
lab.append(eoc("PF_HML_away_lab", [{"run_eocs": "PF_AWL_open"}]))
lab.append(eoc("PF_HML_keep_open", [{"run_eoc_selector": [i for i, n, d, e in KLR], "names": [n for i, n, d, e in KLR], "descriptions": [d for i, n, d, e in KLR],
                                     "keys": [(string.ascii_lowercase + string.ascii_uppercase)[k] for k in range(len(KLR))], "title": "Keep lab (v0.6)", "allow_cancel": True}]))
lab.append(eoc("PF_HML_open", [{"run_eoc_selector": [i for i, n, d, e in HLM], "names": [n for i, n, d, e in HLM], "descriptions": [d for i, n, d, e in HLM],
                                "keys": [(string.ascii_lowercase + string.digits + string.ascii_uppercase)[k] for k in range(len(HLM))], "title": "Home lab (v0.4-0.6)", "allow_cancel": True}]))
lab += [{"type": "ter_furn_transform", "id": tid, "furniture": [{"result": fur, "valid_furniture": ["f_null"]}]}
        for tid, fur in (("PF_HML_t_table", "f_table"), ("PF_HML_t_sofa", "f_sofa"), ("PF_HML_t_book", "f_bookcase"), ("PF_HML_t_piano", "f_piano"))]
files["lab_home.json"] = lab + [{"type": "ter_furn_transform", "id": "PF_LAB_t_deepwater",
                                  "terrain": [{"result": "t_water_dp", "valid_flags": ["DIGGABLE"]}, {"result": "t_water_dp", "valid_flags": ["FLAT"]}]}]

# ============================================================ MOD INTERACTIONS (soft: load only with the other mod)
MI = {}
def nearest_adult(tag):  # inline EOC ids must be unique across the whole mod (both interaction files are checked together)
  return [m("pf_mi_d = 99"), {"u_location_variable": g("pf_mi_av")},
    {"u_run_npc_eocs": [{"id": "PF_MI_near_" + tag, "condition": ADULT, "effect": [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_mi_av) < pf_mi_d"), "then": [m("pf_mi_d = distance(u_pf_pos, pf_mi_av)"), {"u_set_talker": g("pf_mi_who")}]}]}],
     "local": True, "npc_range": 15}]
MI["mindovermatter/pf_telepathy.json"] = [
    eoc("PF_MOM_distress", [{"run_eocs": "PF_MOM_distress_do"}],
        "Signal: an NPC is badly hurt (torso at 40% or less).  See PF_MOM_distress_do.",
        condition={"and": ["has_alpha", "u_is_npc", m("u_hp('torso') <= u_hp_max('torso') * 0.4")]},
        eoc_type="EVENT", required_event="character_takes_damage"),
    eoc("PF_MOM_lab", nearest_adult("mom") + [
        m("pf_mi_had = 1"),
        {"if": {"not": {"u_has_trait": "TELEPATH"}}, "then": [m("pf_mi_had = 0"), {"u_add_trait": "TELEPATH"}]},
        m("pf_mom_last = -1"), m("pf_mom_force = 1"),
        {"if": m("pf_mi_d < 99"), "then": [{"run_eocs": "PF_MOM_distress_do", "alpha_talker": g("pf_mi_who")}], "else": [say("[home lab] Nobody within 15 tiles.")]},
        m("pf_mom_force = 0"),
        {"if": m("pf_mi_had == 0"), "then": [{"u_lose_trait": "TELEPATH"}]},
    ], "Home lab (Mind Over Matter loaded): as if the nearest adult were badly hurt and you were a telepath who cares."),
    eoc("PF_MOM_lab_poll", [{"run_eocs": "PF_MOM_lab"}, m("pf_mi_mom_done = 1")],
        "The Home lab only sets pf_mi_test; this file (loaded only with Mind Over Matter) picks it up, so the main mod never names an EOC that may not exist.",
        recurrence="1 minutes", **{"global": True}, condition={"and": [m("value_or(pf_mi_test, 0) == 1"), m("value_or(pf_mi_mom_done, 0) == 0")]}),
    eoc("PF_MOM_distress_do", [
        {"run_eocs": "PF_ID_ensure"},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_mom_who")},
        name_into("pf_mom_name"),
        m("pf_mom_bond = 0"),
        {"if": {"or": [{"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}, {"compare_string": [{"u_val": "pf_mom"}, "AVATAR"]},
                       {"compare_string": [{"u_val": "pf_dad"}, "AVATAR"]}, {"compare_string": [{"u_val": "pf_guardian"}, "AVATAR"]}]},
         "then": [m("pf_mom_bond = 1")]},
        {"run_eocs": "PF_MOM_sense", "alpha_talker": "avatar"},
    ], "u = an NPC who is badly hurt.  If you're an awakened telepath and they're yours (partner, child, ward) or you care about them a lot (warmth 60+), you feel it, wherever they are in the bubble.  Once every 30 minutes at most."),
    eoc("PF_MOM_sense", [
        {"copy_var": g("pf_mom_who"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        {"if": {"or": [m("pf_mom_bond == 1"), m("pf_read_w >= 60"), m("value_or(pf_mom_force, 0) == 1")]}, "then": [
            m("pf_mom_last = time('now')"),
            say("A spike of fear that isn't yours goes through you: <global_val:pf_mom_name> is hurt, and scared.", "bad")]},
    ], "u = you.", condition={"and": [{"u_has_trait": "TELEPATH"}, cooldown_ok_c("pf_mom_last", "30 m")]}),
]
MI["xedra_evolved/pf_vampire.json"] = [
    eoc("PF_XE_tick", [
        {"u_run_npc_eocs": ["PF_XE_notice"], "local": True, "npc_range": 10},
    ], "Every hour: if you walk the vampire's path (Xedra Evolved), the people close to you may find out.  Each adult within 10 tiles who doesn't know yet has a 1 in 10 chance an hour.",
        recurrence="1 hours", **{"global": True},
        condition={"or": [{"u_has_trait": "VAMPIRE2"}, {"u_has_trait": "VAMPIRE3"}]}),
    eoc("PF_XE_notice", [
        {"run_eocs": "PF_ID_ensure"},
        m("u_pf_xe_knows = 1"), name_into("pf_say_a"),
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        {"if": {"and": [m("pf_read_w >= 45"), m("pf_read_t >= 35")]},
         "then": [{"run_eocs": "PF_XE_keep", "alpha_talker": "avatar"},
                  m("pf_m_str_in = 70"), {"run_eocs": "PF_MK_secret_kept", "beta_talker": "avatar"}],
         "else": [{"run_eocs": "PF_XE_fear", "alpha_talker": "avatar"},
                  {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, m("pf_mv_role = 1"), m("pf_m_str_in = 70"), {"run_eocs": "PF_MV_frightened"}]},
    ], "u = someone near you who now knows.  Warm and trusting (45 / 35): they keep it to themselves (secret_kept: your trust in them jumps).  Otherwise it frightens them (their warmth and trust drop, tension rises).",
        condition={"and": [ADULT, m("value_or(u_pf_xe_knows, 0) == 0"), {"or": [m("rand(9) == 0"), m("value_or(pf_xe_force, 0) == 1")]}]}),
    eoc("PF_XE_lab", nearest_adult("xe") + [
        {"if": m("pf_mi_d < 99"), "then": [m("pf_xe_force = 1"), {"run_eocs": {"id": "PF_XE_lab_one", "effect": [m("u_pf_xe_knows = 0"), {"run_eocs": "PF_XE_notice"}]}, "alpha_talker": g("pf_mi_who")}, m("pf_xe_force = 0")]},
    ], "Home lab (Xedra Evolved loaded): the nearest adult finds out what you are (as if you were a vampire)."),
    eoc("PF_XE_lab_poll", [{"run_eocs": "PF_XE_lab"}, m("pf_mi_xe_done = 1")],
        "See PF_MOM_lab_poll.", recurrence="1 minutes", **{"global": True},
        condition={"and": [m("value_or(pf_mi_test, 0) == 1"), m("value_or(pf_mi_xe_done, 0) == 0")]}),
    eoc("PF_XE_keep", [say("<global_val:pf_say_a> has noticed you never eat, and never stand in the sun.  They don't say anything.  They just start drawing the curtains before you wake.", "good")]),
    eoc("PF_XE_fear", [say("<global_val:pf_say_a> has noticed you never eat, and never stand in the sun.  Now they keep a hand near their knife when you're around.", "bad")]),
]

# ============================================================ WRITE
outdir = os.path.join(ROOT, "home")
os.makedirs(outdir, exist_ok=True)
for name, objs in files.items():
    json.dump(objs, open(os.path.join(outdir, name), "w", encoding="utf-8", newline="\n"), indent=2)
for rel, objs in MI.items():
    path = os.path.join(ROOT, "mod_interactions", *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(objs, open(path, "w", encoding="utf-8", newline="\n"), indent=2)
print("home written:", {k: len(v) for k, v in files.items()}, "| interactions:", list(MI))
