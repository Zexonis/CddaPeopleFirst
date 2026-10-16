"""Generates mods/PeopleFirst/town/*.json: v0.5 "Town", pass 1: the farm (concept section 13).

A name for the place, animals (neighbors bring them; ones you tamed count too) and the morning milk and eggs, a field that
is planted in spring or summer and harvested about a month later (real produce at home), the harvest festival, and two
jobs, herder (6) and farmer (7), added to the household roles in gen_home.py.
Everything hangs off the home (gen_home.py: pf_home_set, pf_home_loc); nothing happens without one.

Usage:  python tools/gen_town.py mods/PeopleFirst
"""
import json, os, sys

ROOT = sys.argv[1]
OUT = os.path.join(ROOT, "town")
os.makedirs(OUT, exist_ok=True)

def m(e): return {"math": [e]}
def g(n): return {"global_val": n}
PARTS = ["torso", "head", "eyes", "mouth", "arm_l", "arm_r", "hand_l", "hand_r", "leg_l", "leg_r", "foot_l", "foot_r"]
def any_part(*effects):
    """u has one of these effects on any body part (a bare u_has_effect checks only the whole-body slot; see gen_life.any_part)."""
    return {"or": [{"u_has_effect": e, "bodypart": bp} for e in effects for bp in PARTS] + [{"u_has_effect": e} for e in effects]}
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
def line(key): return {"run_eocs": "PF_SAY_town", "alpha_talker": "avatar", "variables": {"line": key}}
CALM = "value_or(pf_set_chatter, 1) == 1"
AT_HOME = "value_or(pf_home_set, 0) == 1"
TODAY = "floor(time('now') / time('1 d'))"
HOUR = "time_since('midnight', 'unit': 'hours')"
ADULT = {"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18")]}
LIVESTOCK = {"mon_cow": "cows", "mon_goat": "goats", "mon_chicken": "hens"}
def count_at_home(mon): return f"monsters_nearby('{mon}', 'radius': 25, 'location': pf_home_loc, 'attitude': 'friendly')"
# growing time in days, by the Growing up setting (0 realistic, 1 accelerated (default), 2 fast for testing)
GROW_DAYS = "(value_or(pf_set_grow, 1) == 0 ? 90 : (value_or(pf_set_grow, 1) == 1 ? 30 : 2))"
files = {}

# ---------------------------------------------------------------- spells: neighbors' animals (friendly, permanent)
SPELLS = []
for sid, mon, n in (("PF_SPELL_hens", "mon_chicken", 2), ("PF_SPELL_goat", "mon_goat", 1), ("PF_SPELL_cow", "mon_cow", 1)):
    SPELLS.append({"type": "SPELL", "id": sid, "name": "Neighbors' animals", "description": "People First: animals given by neighbors.  Not a real spell.",
                   "flags": ["SILENT", "PERMANENT", "NO_FAIL", "NO_EXPLOSION_SFX", "NO_HANDS", "NO_LEGS", "NON_MAGICAL"],
                   "valid_targets": ["ground"], "min_damage": n, "max_damage": n, "min_aoe": 2, "max_aoe": 2,
                   "effect": "summon", "effect_str": mon, "min_duration": 100, "max_duration": 100, "shape": "blast"})
files["defs.json"] = SPELLS + [
    {"type": "morale_type", "id": "PF_morale_feast", "text": "The harvest feast"},
    {"type": "ter_furn_transform", "id": "PF_TOWN_t_plant",
     "terrain": [{"result": "t_dirtmound", "valid_terrain": ["t_dirt", "t_grass", "t_grass_long", "t_grass_dead", "t_grass_tall", "t_grass_golf", "t_grass_white"]}]},
    {"type": "ter_furn_transform", "id": "PF_TOWN_t_harvest", "terrain": [{"result": "t_dirt", "valid_terrain": ["t_dirtmound"]}]},
]

# ---------------------------------------------------------------- the name, and the Home menu entries
files["town.json"] = [
    eoc("PF_TOWN_name", [
        {"set_string_var": "", "target_var": g("pf_town_name_in"),
         "string_input": {"title": "What do you call this place?", "description": "A name for your home.  The people who live here will use it.  (Leave it empty to keep it as it is.)",
                          "width": 30, "identifier": "pf_town_name"}},
        {"if": {"not": {"compare_string": [g("pf_town_name_in"), ""]}}, "then": [
            {"copy_var": g("pf_town_name_in"), "target_var": g("pf_town_name")}, m("pf_town_named = 1"), line("named")]},
    ], "u = avatar.  Home menu: Name this place.", condition=m(AT_HOME)),
    eoc("PF_TOWN_status", [
        m("pf_tw_cows = " + count_at_home("mon_cow")), m("pf_tw_goats = " + count_at_home("mon_goat")), m("pf_tw_hens = " + count_at_home("mon_chicken")),
        # full run: "1 people live here"
        {"if": m("pf_hm_res == 1"), "then": [{"set_string_var": "1 person lives", "target_var": g("pf_tw_restxt")}],
         "else": [{"set_string_var": "<global_val:pf_hm_res> people live", "target_var": g("pf_tw_restxt"), "parse_tags": True}]},
        {"if": m("value_or(pf_town_named, 0) == 1"), "then": [line("status_named")], "else": [line("status")]},
        {"switch": m("value_or(pf_field_state, 0)"), "cases": [
            {"case": 0, "effect": [line("field_none")]}, {"case": 1, "effect": [line("field_fallow")]},
            {"case": 2, "effect": [m(f"pf_tw_days = round({GROW_DAYS} - (time('now') - pf_field_t) / time('1 d'))"),
                                     # full run day 93: "About 1 days to the harvest."
                                     {"if": m("pf_tw_days <= 1"), "then": [line("field_growing_1")], "else": [line("field_growing")]}]},
            {"case": 3, "effect": [line("field_ready")]}]},
    ], "u = avatar.  Home menu: How the place is doing.", condition=m(AT_HOME)),
    eoc("PF_TOWN_field_here", [
        {"u_location_variable": g("pf_field_loc")}, m("pf_field_state = 1"), line("field_marked"),
    ], "u = avatar.  Home menu: Plant a field here.  Marks a 5x5 plot centered on you (within 30 tiles of home); it's planted in spring or summer.",
        condition={"and": [m(AT_HOME)]}),
    eoc("PF_TOWN_ask_animals", [
        m("pf_animals_asked = time('now')"), m("pf_animals_due = 1"), line("animals_asked"),
    ], "u = avatar.  Home menu: Ask the neighbors for animals (once a week, when there are other people out there).  They arrive the next morning you're home.",
        condition={"and": [m(AT_HOME), m("value_or(pf_band_n, 0) > 0"), m("value_or(pf_animals_asked, -1) < time('now') - time('7 d')")]}),
    eoc("PF_TOWN_animals_arrive", [
        m("pf_animals_due = 0"), m("_r = rand(5)"),
        {"if": m("_r <= 2"), "then": [{"u_cast_spell": {"id": "PF_SPELL_hens"}, "loc": g("pf_home_loc")}, {"set_string_var": "two hens in a crate", "target_var": g("pf_say_b")}]},
        {"if": {"and": [m("_r >= 3"), m("_r <= 4")]}, "then": [{"u_cast_spell": {"id": "PF_SPELL_goat"}, "loc": g("pf_home_loc")}, {"set_string_var": "a nanny goat on a rope", "target_var": g("pf_say_b")}]},
        {"if": m("_r == 5"), "then": [{"u_cast_spell": {"id": "PF_SPELL_cow"}, "loc": g("pf_home_loc")}, {"set_string_var": "a cow, of all things", "target_var": g("pf_say_b")}]},
        line("animals_arrive"), m("pf_animals_total = value_or(pf_animals_total, 0) + 1"),
    ], "u = avatar, at home in the morning.  Hens (most often), a goat, or now and then a cow, given by neighbors: friendly and permanent (a summon spell cast at home)."),
]

# ---------------------------------------------------------------- the morning: animals arrive, milk and eggs, the field
files["farm.json"] = [
    eoc("PF_TOWN_morning", [
        m(f"pf_tw_day = {TODAY}"),
        {"u_location_variable": g("pf_tw_av")},
        {"if": m("distance(pf_tw_av, pf_home_loc) <= 30"), "then": [
            {"if": m("value_or(pf_animals_due, 0) == 1"), "then": [{"run_eocs": "PF_TOWN_animals_arrive"}]},
            {"run_eocs": "PF_TOWN_produce"},
            {"run_eocs": "PF_TOWN_field_tick"}]},
    ], "Once a day, 07:00-18:00, when you're home and awake: neighbors' animals arrive, the animals give milk and eggs, and the field moves along.",
        recurrence="30 minutes", **{"global": True},
        # playtest 3: planting day ("everyone pitches in") happened while you slept; the morning waits for you to be up
        condition={"and": [m(AT_HOME), {"not": {"u_has_effect": "sleep"}}, m(f"{HOUR} >= 7"), m(f"{HOUR} < 18"), m(f"value_or(pf_tw_day, -1) != {TODAY}")]}),
    eoc("PF_TOWN_worker", [
        m("pf_tw_wbest = -1"),
        {"u_run_npc_eocs": [{"id": "PF_TOWN_worker_cand", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), {"not": {"u_has_effect": "sleep"}}]},
                             "effect": [m("_s = (value_or(u_pf_role, 0) == pf_tw_role) * 100 + u_skill('survival') * 5 + rand(10)"),
                                        {"if": m("_s > pf_tw_wbest"), "then": [m("pf_tw_wbest = _s"), name_into("pf_say_a"), {"u_set_talker": g("pf_tw_worker")}]}]}],
         "local": True, "npc_range": 40},
    ], "u = avatar.  pf_tw_role = the job wanted (6 herder, 7 farmer).  Picks the resident with that job, else the most able resident; pf_tw_wbest < 0 means nobody."),
    eoc("PF_TOWN_produce", [
        m("pf_tw_cows = " + count_at_home("mon_cow")), m("pf_tw_goats = " + count_at_home("mon_goat")), m("pf_tw_hens = " + count_at_home("mon_chicken")),
        {"if": m("pf_tw_cows + pf_tw_goats + pf_tw_hens > 0"), "then": [
            m("pf_tw_role = 6"), {"run_eocs": "PF_TOWN_worker"},
            m("pf_tw_jugs = pf_tw_cows + pf_tw_goats"), m("pf_tw_eggs = 0"), m("pf_tw_eggs_i = 0"),
            {"run_eocs": "PF_TOWN_lay", "condition": m("pf_tw_eggs_i < pf_tw_hens"), "iterations": 20},
            m("pf_tw_mi = 0"),
            {"run_eocs": "PF_TOWN_milk_cow", "condition": m("pf_tw_mi < pf_tw_cows"), "iterations": 20}, m("pf_tw_mi = 0"),
            {"run_eocs": "PF_TOWN_milk_goat", "condition": m("pf_tw_mi < pf_tw_goats"), "iterations": 20},
            {"if": m("pf_tw_eggs > 0"), "then": [{"map_spawn_item": "egg_chicken", "loc": g("pf_stores_loc"), "count": {"global_val": "pf_tw_eggs"}}]},
            {"if": m("pf_tw_jugs + pf_tw_eggs > 0"), "then": [
                m("pf_milk_total = value_or(pf_milk_total, 0) + pf_tw_jugs"), m("pf_eggs_total = value_or(pf_eggs_total, 0) + pf_tw_eggs"),
                m("pf_stores = value_or(pf_stores, 0) + pf_tw_jugs + pf_tw_eggs / 2"),
                {"if": m(CALM), "then": [
                    {"if": m("pf_tw_wbest >= 0"),
                     "then": [{"if": m("(pf_tw_jugs > 0) * (pf_tw_eggs > 0)"), "then": [line("produce_both")],
                               "else": [{"if": m("pf_tw_jugs > 0"), "then": [line("produce_milk")], "else": [line("produce_eggs")]}]}],
                     "else": [line("produce_you")]},
                    {"if": m("rand(3) == 0"), "then": [{"run_eocs": "PF_TOWN_kid_animals"}]}]}]}]},
    ], "u = avatar.  The herder (or the most able resident, or you) brings in the morning's milk (a jug per cow, about 2 liters; per goat, about 3/4 liter) and eggs (each hen half the time), as real items at home."),
    eoc("PF_TOWN_milk_cow", [{"map_spawn_item": "milk_raw", "loc": g("pf_stores_loc"), "count": 8, "container": "jug_plastic"}, m("pf_tw_mi += 1")],
        "A cow's morning milk: about 2 liters in a gallon jug (count = servings)."),
    eoc("PF_TOWN_milk_goat", [{"map_spawn_item": "milk_raw", "loc": g("pf_stores_loc"), "count": 3, "container": "jug_plastic"}, m("pf_tw_mi += 1")],
        "A goat's morning milk: about three quarters of a liter."),
    eoc("PF_TOWN_lay", [{"if": m("rand(1) == 0"), "then": [m("pf_tw_eggs += 1")]}, m("pf_tw_eggs_i += 1")]),
    eoc("PF_TOWN_kid_animals", [
        m("pf_tw_kid = 0"),
        {"u_run_npc_eocs": [{"id": "PF_TOWN_kid_cand", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}, m("pf_tw_kid == 0")]},
                             "effect": [m("pf_tw_kid = 1"), name_into("pf_say_b")]}], "local": True, "npc_range": 40},
        {"if": m("pf_tw_kid == 1"), "then": [
            {"if": m("pf_tw_hens > 0"), "then": [{"if": m("rand(1) == 0"), "then": [line("kid_hens")], "else": [line("kid_eggs")]}],
             "else": [line("kid_named")]}]},
    ], "u = avatar.  A child and the animals: chasing the hens, carrying the eggs, naming the goat."),
    # ---------------------------------------------------------------- the field
    eoc("PF_TOWN_field_tick", [
        {"if": {"and": [m("value_or(pf_field_state, 0) == 1"), {"or": [{"is_season": "spring"}, {"is_season": "summer"}]}]}, "then": [{"run_eocs": "PF_TOWN_plant"}],
         "else": [{"if": {"and": [m("value_or(pf_field_state, 0) == 2"), m(f"time('now') - pf_field_t >= time('1 d') * {GROW_DAYS}")]},
                   "then": [{"run_eocs": "PF_TOWN_harvest"}]}]},
    ], "u = avatar.  Fallow and in season: plant.  Grown: harvest."),
    eoc("PF_TOWN_plant", [
        m("pf_tw_role = 7"), {"run_eocs": "PF_TOWN_worker"},
        {"u_transform_radius": 2, "ter_furn_transform": "PF_TOWN_t_plant", "target_var": g("pf_field_loc")},
        m("pf_field_state = 2"), m("pf_field_t = time('now')"), m("pf_plantings_total = value_or(pf_plantings_total, 0) + 1"),
        {"if": m(CALM), "then": [{"if": m("pf_tw_wbest >= 0"), "then": [line("planting_day")], "else": [line("planting_you")]}]},
        {"u_run_npc_eocs": [{"id": "PF_TOWN_plant_helper", "condition": {"and": [m("value_or(u_pf_resident, 0) == 1"), {"not": {"u_has_effect": "sleep"}}]},
                             "effect": [m("pf_m_str_in = 25"), {"run_eocs": "PF_MK_fire_evening", "beta_talker": "avatar"}]}], "local": True, "npc_range": 30},
    ], "u = avatar.  Planting day: the farmer (or anyone who lives with you) plants the plot (dirt mounds); everyone who lives here pitches in (a small shared moment with you)."),
    eoc("PF_TOWN_harvest", [
        m("pf_tw_role = 7"), {"run_eocs": "PF_TOWN_worker"},
        {"u_transform_radius": 2, "ter_furn_transform": "PF_TOWN_t_harvest", "target_var": g("pf_field_loc")},
        {"map_spawn_item": "potato", "loc": g("pf_stores_loc"), "count": 12},
        {"map_spawn_item": "carrot", "loc": g("pf_stores_loc"), "count": 10},
        {"map_spawn_item": "cabbage_head", "loc": g("pf_stores_loc"), "count": 4},
        m("pf_field_state = 1"), m(f"pf_harvest_day = {TODAY}"), m("pf_stores = value_or(pf_stores, 0) + 20"), m("pf_harvests_total = value_or(pf_harvests_total, 0) + 1"),
        {"if": m(CALM), "then": [{"if": m("pf_tw_wbest >= 0"), "then": [line("harvest")], "else": [line("harvest_you")]}]},
    ], "u = avatar.  The harvest: real potatoes, carrots and cabbages at home; the plot goes back to dirt and waits for the next season.  Tonight is the feast."),
    # ---------------------------------------------------------------- the harvest festival (called from the evening beat, gen_life)
    eoc("PF_TOWN_feast", [
        m(f"pf_feast_day = {TODAY}"),
        {"if": m("value_or(pf_town_named, 0) == 1"), "then": [line("feast_named")], "else": [line("feast")]},
        {"u_add_morale": "PF_morale_feast", "bonus": 15, "max_bonus": 15, "duration": "12 hours", "decay_start": "6 hours"},
        {"u_run_npc_eocs": [{"id": "PF_TOWN_feast_one", "condition": m("has_var(u_pf_uid)"),
                             "effect": [m("pf_m_str_in = 40"), {"run_eocs": "PF_MK_meal_shared", "beta_talker": "avatar"}]}], "local": True, "npc_range": 20},
    ], "u = avatar, at the evening beat on the day of a harvest: the evening becomes a feast (morale, and a shared meal with everyone there).",
        condition={"and": [m(f"value_or(pf_harvest_day, -1) == {TODAY}"), m(f"value_or(pf_feast_day, -1) != {TODAY}")]}),
]

# ---------------------------------------------------------------- lines
A, B = "<global_val:pf_say_a>", "<global_val:pf_say_b>"
TN = "<global_val:pf_town_name>"
LINES = {
    "named": (f"From now on, this place is {TN}.", "good"),
    "status": ("Home: <global_val:pf_tw_restxt> here.  Animals: cows <global_val:pf_tw_cows>, goats <global_val:pf_tw_goats>, hens <global_val:pf_tw_hens>.", "info"),
    "status_named": (f"{TN}: <global_val:pf_tw_restxt> here.  Animals: cows <global_val:pf_tw_cows>, goats <global_val:pf_tw_goats>, hens <global_val:pf_tw_hens>.", "info"),
    "field_none": ("There's no field yet.", "info"),
    "field_fallow": ("The field lies waiting for spring or summer.", "info"),
    "field_growing": ("The field is growing.  About <global_val:pf_tw_days> days to the harvest.", "info"),
    "field_growing_1": ("The field is nearly ready.  The harvest is a day away, maybe less.", "info"),
    "field_ready": ("The field is ready to bring in.", "good"),
    "field_marked": ("You pace out a plot here.  It'll be planted when the season is right.", "info"),
    "animals_asked": ("You put the word out that you could use some animals.  Someone always knows someone.", "info"),
    "animals_arrive": (f"Neighbors turn up in the morning with {B}.  \"For the place.  You'd do the same.\"", "good"),
    "produce_both": (f"{A} brings in the milk and a basket of eggs, still warm.", "good"),
    "produce_milk": (f"{A} comes back from the animals with the morning's milk.", "good"),
    "produce_eggs": (f"{A} checks under the hens and comes back with a handful of eggs.", "good"),
    "produce_you": ("You see to the animals yourself this morning: milk, eggs, the lot.", "info"),
    "kid_hens": (f"{B} chases the hens round the yard until one of them turns and chases back.", "info"),
    "kid_eggs": (f"{B} insists on carrying the eggs, one at a time, very slowly.", "info"),
    "kid_named": (f"{B} has given every animal a name.  None of the names make sense.  All of them stick.", "info"),
    "planting_day": (f"Planting day.  {A} lays out the rows and everyone pitches in.  By noon everybody has dirt to the elbows.", "good"),
    "planting_you": ("You plant the field yourself, row by row.  It takes all morning.", "info"),
    "harvest": (f"{A} brings the harvest in: potatoes, carrots, cabbages, more than anyone expected.", "good"),
    "harvest_you": ("You bring the harvest in yourself: potatoes, carrots, cabbages.", "good"),
    "feast": ("Tonight there's more food than anyone can eat.  Somebody gets out an instrument and nobody wants to go to bed.", "good"),
    "feast_named": (f"Tonight {TN} eats like it's before.  Somebody gets out an instrument and nobody wants to go to bed.", "good"),
    "chore_herder": (f"{A} walks the animals out to graze and back again, talking to them the whole way.", "info"),
    "chore_farmer": (f"{A} spends the afternoon on their knees in the field, pulling weeds and swearing at slugs.", "info"),
}
files["lines.json"] = [eoc("PF_SAY_town", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Town lines, picked by the context var 'line'.")]

# ---------------------------------------------------------------- lab (added to the Home lab by gen_home.py: PF_TL_* entries are listed there)
files["lab_town.json"] = [
    eoc("PF_TL_animals", [m("pf_animals_due = 1"), {"run_eocs": "PF_TOWN_animals_arrive"}],
        "Town lab: the neighbors' animals arrive now (at home)."),
    eoc("PF_TL_morning", [m("pf_tw_day = -1"), {"run_eocs": "PF_TOWN_produce"}, {"run_eocs": "PF_TOWN_field_tick"}],
        "Town lab: run this morning's milk, eggs and field step now."),
    eoc("PF_TL_grow", [{"if": m("value_or(pf_field_state, 0) == 2"), "then": [m("pf_field_t = time('now') - time('120 d')"), say("[town lab] The field is grown.")],
                        "else": [say("[town lab] Nothing is planted.")]}],
        "Town lab: the planted field is ready (next morning step harvests it)."),
    eoc("PF_TL_feast", [m(f"pf_harvest_day = {TODAY}"), m("pf_feast_day = -1"), {"run_eocs": "PF_TOWN_feast"}],
        "Town lab: tonight's harvest feast, now."),
    eoc("PF_TL_stats", [
        m("pf_hs_a = value_or(pf_milk_total, 0)"), m("pf_hs_b = value_or(pf_eggs_total, 0)"), m("pf_hs_c = value_or(pf_plantings_total, 0)"),
        m("pf_hs_d = value_or(pf_harvests_total, 0)"), m("pf_hs_e = value_or(pf_animals_total, 0)"),
        say("[town lab] milk <global_val:pf_hs_a> jugs, eggs <global_val:pf_hs_b>, plantings <global_val:pf_hs_c>, harvests <global_val:pf_hs_d>, animal gifts <global_val:pf_hs_e>.")]),
]


# ============================================================ PASS 2: the working town (smith, healer, teacher, market day)
# Stores: what the place has to spare (milk, eggs, harvest), counted as it comes in; market day turns it into goods.
def job_worker(role, out):
    """Effects that find the resident with this job (any adult resident if strict is off) into talker global `out`; pf_tw_wbest < 0 = nobody."""
    return [m(f"pf_tw_role = {role}"), {"run_eocs": "PF_TOWN_worker"}, m("pf_tw_wjob = pf_tw_wbest >= 100")]
SMITH_GOODS = [("nail", 30, "a bucket of nails"), ("knife_hunting", 1, "a hunting knife, edge like a razor"), ("machete", 1, "a machete, rough but true"),
               ("crowbar", 1, "a crowbar out of an old axle"), ("bolt_metal", 10, "a bundle of crossbow bolts")]
MARKET_GOODS = [("bandages", 5, "bandages"), ("aspirin", 10, "a bottle of aspirin"), ("antibiotics", 2, "a few antibiotics"), ("salt", 10, "salt"),
                ("soap", 3, "soap"), ("candle", 5, "candles"), ("seed_potato_raw", 10, "seed potatoes")]
SCHOOL = ["sits the children in a row under the nearest tree and teaches them their letters, with a stick in the dirt.",
          "has the kids tying knots until they can do it with their eyes shut.",
          "teaches the children how to tell which berries will kill you.  They listen to that one."]
smith_eff = [m(f"_g = rand({len(SMITH_GOODS) - 1})")] + [
    {"if": m(f"_g == {i}"), "then": [{"map_spawn_item": it, "loc": g("pf_stores_loc"), "count": n}, {"set_string_var": txt, "target_var": g("pf_say_b")}]}
    for i, (it, n, txt) in enumerate(SMITH_GOODS)]
market_one = [m(f"_g = rand({len(MARKET_GOODS) - 1})")] + [
    {"if": m(f"_g == {i}"), "then": [{"map_spawn_item": it, "loc": g("pf_stores_loc"), "count": n}, {"set_string_var": txt, "target_var": g("pf_mk_last")}]}
    for i, (it, n, txt) in enumerate(MARKET_GOODS)]
school_eff = [m(f"_p = rand({len(SCHOOL) - 1})")] + [
    {"if": m(f"_p == {i}"), "then": [{"set_string_var": f"<global_val:pf_sc_who> {t}", "target_var": g("pf_sc_text"), "parse_tags": True}]} for i, t in enumerate(SCHOOL)]
files["work.json"] = [
    eoc("PF_TOWN_workday", [
        m(f"pf_wd_day = {TODAY}"),
        {"u_location_variable": g("pf_tw_av")},
        {"if": m("distance(pf_tw_av, pf_home_loc) <= 30"), "then": [
            {"run_eocs": "PF_TOWN_school"},
            {"run_eocs": "PF_TOWN_healer_round"},
            {"if": m("time('now') - value_or(pf_smith_t, 0) >= time('3 d')"), "then": [{"run_eocs": "PF_TOWN_smithy"}]},
            {"if": {"and": [m(f"{TODAY} % 7 == 6"), m("value_or(pf_band_n, 0) > 0"), m("value_or(pf_residents_n, 0) >= 2")]}, "then": [{"run_eocs": "PF_TOWN_market"}]}]},
    ], "Once a day, 09:00-12:00, when you're home: school, the healer's round, the smithy (every 3 days), and on the seventh day the market (once at least two people live with you: playtest 3 had neighbors turning up for market day at a lone evac shelter).",
        recurrence="30 minutes", **{"global": True},
        condition={"and": [m(AT_HOME), m(f"{HOUR} >= 9"), m(f"{HOUR} < 12"), m(f"value_or(pf_wd_day, -1) != {TODAY}"), m("(value_or(pf_law_rest, 0) == 1) * (floor(time('now') / time('1 d')) % 7 == 2) == 0")]}),
    eoc("PF_TOWN_school", job_worker(10, "pf_tw_worker") + [
        {"if": m("pf_tw_wjob"), "then": [
            m("pf_sc_n = 0"), m("pf_tk_quiet = 1"), {"copy_var": g("pf_say_a"), "target_var": g("pf_sc_who")},
            {"u_run_npc_eocs": [{"id": "PF_TOWN_pupil", "condition": {"and": [{"u_has_trait": "PF_CHILD"}, {"not": {"u_has_effect": "PF_infant"}}, m("u_val('age') >= 4"),
                                                                              m("value_or(u_pf_taught_t, -1) < time('now') - time('1 d')")]},
                                 "effect": [m("pf_sc_n += 1"), {"run_eocs": "PF_FAM_teach_do", "alpha_talker": g("pf_tw_worker"), "beta_talker": "u"}]}],
             "local": True, "npc_range": 40},
            m("pf_tk_quiet = 0"),
            {"if": m("pf_sc_n > 0"), "then": school_eff + [m("pf_school_total = value_or(pf_school_total, 0) + 1"), {"if": m(CALM), "then": [line("school")]}]}]},
    ], "u = avatar.  Morning school: the teacher (job 10) teaches every child of 4 or more who hasn't learned anything today (the v0.4 teaching moment, quietly), with one line for the whole class."),
    eoc("PF_TOWN_healer_round", job_worker(9, "pf_tw_worker") + [
        {"if": m("pf_tw_wjob"), "then": [
            m("pf_hr_n = 0"),
            {"u_run_npc_eocs": [{"id": "PF_TOWN_patient", "condition": {"and": [m("has_var(u_pf_uid)"), {"or": [any_part("bite", "infected", "bleed"),
                                                                                                            m("u_hp('torso') < u_hp_max('torso') * 0.9")]}]},
                                 "effect": [m("pf_hr_n += 1"), {"u_lose_effect": ["bite", "infected", "bleed"], "target_part": "ALL"},
                                            m("u_hp('torso') = min(u_hp('torso') + 5, u_hp_max('torso'))")]}], "local": True, "npc_range": 40},
            {"if": any_part("bite", "infected", "bleed"), "then": [
                m("pf_hr_n += 1"), {"u_lose_effect": ["bite", "infected", "bleed"], "target_part": "ALL"},
                m("pf_m_str_in = 45"), {"run_eocs": "PF_MK_care_given", "alpha_talker": g("pf_tw_worker"), "beta_talker": "avatar"}]},
            {"if": {"and": [m("pf_hr_n > 0"), m(CALM)]}, "then": [line("healer_round")]},
            m("pf_healed_total = value_or(pf_healed_total, 0) + pf_hr_n")]},
    ], "u = avatar.  The healer (job 9) goes round once a day: bites, infections and bleeding are treated, and anyone a little hurt gets patched up (you too: a care moment)."),
    eoc("PF_TOWN_smithy", job_worker(8, "pf_tw_worker") + [
        {"if": m("pf_tw_wjob"), "then": [m("pf_smith_t = time('now')")] + smith_eff + [
            m("pf_smith_total = value_or(pf_smith_total, 0) + 1"), {"if": m(CALM), "then": [line("smith")]}]},
    ], "u = avatar.  Every 3 days the smith (job 8) turns scrap into something useful: nails, a knife, a machete, a crowbar or bolts (real items at home)."),
    eoc("PF_TOWN_market", [
        m("pf_mk_n = 0"), {"set_string_var": "", "target_var": g("pf_mk_list")},
        # full run day 139: "nothing to spare" beside full shelves; up to a third of the real stores go to the handcarts
        m("pf_dr_want = 30"), m("pf_dr_div = 3"), {"run_eocs": "PF_STORES_draw", "alpha_talker": "avatar"},
        {"run_eocs": "PF_TOWN_market_buy", "condition": {"and": [m("value_or(pf_stores, 0) >= 10"), m("pf_mk_n < 3")]}, "iterations": 4},
        {"if": m("pf_mk_n > 0"),
         "then": [m("pf_markets_total = value_or(pf_markets_total, 0) + 1"),
                  {"u_run_npc_eocs": [{"id": "PF_TOWN_market_meal", "condition": m("value_or(u_pf_resident, 0) == 1"),
                                       "effect": [m("pf_m_str_in = 25"), {"run_eocs": "PF_MK_meal_shared", "beta_talker": "avatar"}]}], "local": True, "npc_range": 30},
                  {"if": m("value_or(pf_town_named, 0) == 1"), "then": [line("market_named")], "else": [line("market")]}],
         "else": [{"if": m(CALM), "then": [line("market_none")]}]},
    ], "u = avatar.  Market day (every seventh day, when there are other people out there): neighbors come with handcarts, and each 10 of the place's stores becomes something you need (up to 3 goods, real items at home).  A meal shared with everyone who lives here."),
    eoc("PF_TOWN_market_buy", market_one + [
        m("pf_stores -= 10"), m("pf_mk_n += 1"),
        {"if": m("pf_mk_n == 1"), "then": [{"copy_var": g("pf_mk_last"), "target_var": g("pf_mk_list")}],
         "else": [{"set_string_var": "<global_val:pf_mk_list>, <global_val:pf_mk_last>", "target_var": g("pf_mk_list"), "parse_tags": True}]},
    ]),
]
LINES.update({
    "school": ("<global_val:pf_sc_text>", "info"),
    "healer_round": (f"{A} goes round with the medicine bag, checking everyone's cuts and making them drink something foul.", "good"),
    "smith": (f"{A} has been hammering behind the house for two days.  The result: {B}.", "good"),
    "market": ("Market day.  Neighbors come with handcarts, and by the afternoon the place's surplus has turned into <global_val:pf_mk_list>.", "good"),
    "market_named": (f"Market day in {TN}.  Neighbors come with handcarts, and by the afternoon the surplus has turned into <global_val:pf_mk_list>.", "good"),
    "market_none": ("Neighbors come by for market day, but there's nothing to spare this week.  They stay for a cup of something anyway.", "info"),
})
files["lines.json"] = [eoc("PF_SAY_town", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Town lines, picked by the context var 'line'.")]
files["lab_town.json"] += [
    eoc("PF_TL_workday", [m("pf_wd_day = -1"), m("pf_smith_t = 0"), {"run_eocs": "PF_TOWN_school"}, {"run_eocs": "PF_TOWN_healer_round"}, {"run_eocs": "PF_TOWN_smithy"}],
        "Town lab: today's school, healer's round and smithy, now."),
    eoc("PF_TL_market", [m("pf_stores = value_or(pf_stores, 0) + 30"), {"run_eocs": "PF_TOWN_market"}],
        "Town lab: market day now (with 30 stores added)."),
    eoc("PF_TL_stats2", [
        m("pf_hs_a = value_or(pf_school_total, 0)"), m("pf_hs_b = value_or(pf_healed_total, 0)"), m("pf_hs_c = value_or(pf_smith_total, 0)"),
        m("pf_hs_d = value_or(pf_markets_total, 0)"), m("pf_hs_e = value_or(pf_stores, 0)"),
        say("[town lab] school days <global_val:pf_hs_a>, treated <global_val:pf_hs_b>, smithy <global_val:pf_hs_c>, markets <global_val:pf_hs_d>, stores now <global_val:pf_hs_e>.")]),
]

# ============================================================ PASS 3: the town grows (families join) and keeps a watch
# Stories: "One morning the Okafors turned up with their handcart: 'If the offer's still open.'"
#          "Someone's always on the watch.  Tonight it's Dana and Marcus; tomorrow someone else.  Nobody has to ask."
#          "The night they came, it was the watch that saw them first."
def by_uid(eocs, uid): return {"u_run_npc_eocs": eocs, "unique_ids": [uid], "local": False}
NIGHT = "floor((time('now') - time('12 h')) / time('1 d'))"
ON_WATCH = {"and": [m("value_or(u_pf_on_watch, 0) == 1"), m(f"value_or(u_pf_watch_night, -1) == {NIGHT}")]}
WATCH_RECENT = m("value_or(pf_wt_seen_t, -1) >= time('now') - time('3 m')")
HOUSES = 8   # households that can join (house slots pf_house_0..7)

# ---------------------------------------------------------------- the place's draw (what people out there have heard)
APPEAL = [
    m("pf_town_appeal = 10 * value_or(pf_town_named, 0) + 10 * (value_or(pf_animals_total, 0) > 0) + 10 * (value_or(pf_harvests_total, 0) > 0)"
      " + 10 * (value_or(pf_school_total, 0) > 0) + 5 * (value_or(pf_healed_total, 0) > 0) + 10 * (value_or(pf_markets_total, 0) > 0)"
      " + min(value_or(pf_residents_n, 0) * 2, 20) + 10 * (value_or(pf_wt_nights_total, 0) > 0)"
      " + 10 * (value_or(pf_wall_state, 0) == 2) + 10 * (value_or(pf_sieges_held, 0) > 0) + 5 * (value_or(pf_st_pacts, 0) > 0)"
      " - 10 * (time('now') - value_or(pf_horn_t, -999999) < time('3 d'))"),
    m("pf_town_appeal = max(pf_town_appeal, 0)"),
]
house_free = [m("pf_tj_ok = (distance(pf_tj_try, pf_home_loc) >= 12) * (distance(pf_tj_try, pf_home_loc) <= 60)")] + [
    {"if": m(f"value_or(pf_households_n, 0) > {k}"), "then": [{"if": m(f"distance(pf_tj_try, pf_house_{k}) < 8"), "then": [m("pf_tj_ok = 0")]}]} for k in range(HOUSES)]
store_house = [{"if": m(f"pf_households_n == {k}"), "then": [{"copy_var": g("pf_tj_house"), "target_var": g(f"pf_house_{k}")}]} for k in range(HOUSES)]
SETTLE = ["PF_TOWN_settle_one", "PF_HOME_join_one"]

files["join.json"] = [
    eoc("PF_TOWN_appeal", APPEAL, "How much the place draws people: a name, animals, a harvest, a school, a healer, a market, the people who live here (2 each, up to 20) and a watch; a fight in the last 3 days takes 10 off."),
    # -------- the decision (off-screen data: views and visits, nothing loads)
    eoc("PF_TOWN_join_tick", [
        m(f"pf_tj_day = {TODAY}"), {"run_eocs": "PF_TOWN_appeal"},
        m("pf_tj_best = -1"), m("pf_wi = 0"),
        {"run_eocs": "PF_TOWN_join_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
        {"if": m("pf_tj_best >= 0"), "then": [by_uid(["PF_TOWN_join_go"], g("pf_tj_lead"))]},
    ], "Checked hourly, decided once a day between 13:00 and 14:00, one day in four: a settled family that knows you (2+ visits or meals at their place) decides to move to your place if their leader's warmth toward you plus half the place's draw comes to 50 or more.  The best such family packs up and walks over (A-Life waypoints); one family at a time, at most every 3 days, up to 8 households.",
        recurrence="1 hours", **{"global": True},
        condition={"and": [m(AT_HOME), m("value_or(pf_alife_on, 1) == 1"), m(f"{HOUR} >= 13"), m(f"{HOUR} < 14"), m(f"value_or(pf_tj_day, -1) != {TODAY}"),
                           m("value_or(pf_tj_active, 0) == 0"), m(f"value_or(pf_households_n, 0) < {HOUSES}"),
                           m("time('now') - value_or(pf_tj_last, -999999) >= time('3 d')"), m("rand(3) == 0")]}),
    eoc("PF_TOWN_join_i", [
        {"set_string_var": "pf_slot_<global_val:pf_wi>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [by_uid(["PF_TOWN_join_cand"], {"var_val": "ref"})]},
        m("pf_wi += 1"),
    ]),
    eoc("PF_TOWN_join_cand", [
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        m("_s = pf_read_w + pf_town_appeal / 2"),
        {"if": m("value_or(pf_tj_force, 0) == 1"), "then": [m("_s = 10000 - distance(u_pf_vpos, pf_home_loc)")]},
        {"if": {"and": [m("_s >= 50"), m("_s > pf_tj_best")]}, "then": [m("pf_tj_best = _s"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_tj_lead")}]},
    ], "u = a band's leader (by unique id).  Only settled families who know you; their own view of you decides.",
        condition={"and": [m("value_or(u_pf_settled, 0) == 1"), m("value_or(u_pf_visiting, 0) == 0"), m("value_or(u_pf_joining, 0) == 0"), m("has_var(u_pf_home)"),
                           m("distance(u_pf_vpos, pf_home_loc) <= 1000"),
                           {"or": [m("value_or(pf_tj_force, 0) == 1"), m("value_or(u_pf_visits_n, 0) + value_or(u_pf_hosted_n, 0) >= 2")]}]}),
    eoc("PF_TOWN_join_go", [
        m("u_pf_joining = 1"), m("pf_tj_active = 1"), m("pf_tj_since = time('now')"),
        {"copy_var": g("pf_home_loc"), "target_var": {"u_val": "pf_wp_a"}},
        {"location_variable_adjust": {"u_val": "pf_wp_a"}, "x_adjust": 5, "y_adjust": 5},
        {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_wp_b"}},
        {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_goal"}},
        name_into("pf_tj_name"),
        {"if": m(CALM), "then": [line("join_word")]},
    ], "u = a settled family's leader: they pack up everything and head for your place."),
    # -------- the arrival (on-screen, at your door)
    eoc("PF_TOWN_arrive_tick", [
        {"if": m("time('now') - pf_tj_since > time('4 d')"),
         "then": [by_uid(["PF_TOWN_join_back"], g("pf_tj_lead")), m("pf_tj_active = 0")],
         "else": [{"u_location_variable": g("pf_tj_av")},
                  {"if": m("distance(pf_tj_av, pf_home_loc) <= 30"), "then": [
                      {"run_eocs": "PF_THREAT_scan"},
                      m("pf_tj_here = 0"),
                      {"if": m("pf_threat == 0"), "then": [by_uid(["PF_TOWN_arrive_check"], g("pf_tj_lead"))]},
                      {"if": m("pf_tj_here == 1"), "then": [
                          {"if": {"and": [m("value_or(pf_law_dark, 0) == 1"), {"or": [m(f"{HOUR} >= 19"), m(f"{HOUR} < 7")]}]},
                           "then": [{"if": m(f"value_or(pf_tj_dark_night, -1) != {NIGHT}"), "then": [m(f"pf_tj_dark_night = {NIGHT}"),
                                    {"run_eocs": "PF_SAY_keep", "alpha_talker": "avatar", "variables": {"line": "join_dark"}}]}],
                           "else": [{"run_eocs": "PF_TOWN_ask"}]}]}]}]},
    ], "Every 10 minutes while a family is on its way: once they reach your place (within 25 tiles of home) and you're home and it's calm, they ask.  If they haven't arrived in 4 days they give up and go home.",
        recurrence="10 minutes", **{"global": True}, condition={"and": [m("value_or(pf_tj_active, 0) == 1"), m(AT_HOME)]}),
    eoc("PF_TOWN_arrive_check", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_home_loc) <= 25"), "then": [m("pf_tj_here = 1"), name_into("pf_tj_name")]},
    ], "u = the joining family's leader, only when on-screen (online): reading the position of someone off-screen would load the map around them.",
        condition=m("value_or(u_pf_online, 0) == 1")),
    eoc("PF_TOWN_ask", [
        {"if": m("value_or(pf_town_named, 0) == 1"),
         "then": [{"set_string_var": f"<global_val:pf_tj_name> and their family are here, with everything they own on a handcart.  They want to make their home in {TN}.  Will you take them in?",
                   "target_var": g("pf_tj_q"), "parse_tags": True}],
         "else": [{"set_string_var": "<global_val:pf_tj_name> and their family are here, with everything they own on a handcart.  They want to make their home here, with you.  Will you take them in?",
                   "target_var": g("pf_tj_q"), "parse_tags": True}]},
        m("pf_tj_active = 0"),
        {"if": m("value_or(pf_law_door, 0) == 1"), "then": [{"run_eocs": "PF_KEEP_door_vote"}],
         "else": [{"if": m("(value_or(pf_law_council, 0) == 1) * (value_or(pf_cn_n, 0) >= 2)"), "then": [{"run_eocs": "PF_KEEP_council_door"}],
         "else": [{"if": m("value_or(pf_chief_set, 0) == 1"), "then": [{"run_eocs": "PF_KEEP_door"}],
         "else": [{"if": {"u_query": g("pf_tj_q"), "default": True}, "then": [{"run_eocs": "PF_TOWN_join_yes"}], "else": [{"run_eocs": "PF_TOWN_join_no"}]}]}]}]},
    ], "u = avatar.  (v0.6 Keep pass 2: with the door law, the whole meeting votes.)  A yes/no popup: taking a whole family in is your call (v0.6 The Keep: unless someone else is chief, then it's theirs)."),
    eoc("PF_TOWN_join_yes", [
        m("pf_tj_found = 0"),
        {"run_eocs": "PF_TOWN_house_try", "condition": m("pf_tj_found == 0"), "iterations": 8},
        {"if": m("pf_tj_found == 0"), "then": [
            {"copy_var": g("pf_home_loc"), "target_var": g("pf_tj_house")},
            {"location_variable_adjust": g("pf_tj_house"), "x_adjust": m("(rand(1) * 2 - 1) * (10 + rand(4))"), "y_adjust": m("rand(16) - 8")}]},
    ] + store_house + [
        m("pf_households_n = value_or(pf_households_n, 0) + 1"), m("pf_tj_hh = pf_households_n"),
        {"copy_var": g("pf_tj_lead"), "target_var": g("pf_inv_lead")},
        m("pf_hm_i = 0"), {"run_eocs": "PF_HOME_unroster_i", "condition": m("pf_hm_i < pf_band_n"), "iterations": 1000},
        by_uid(["PF_TOWN_join_band"], g("pf_tj_lead")),
        m("pf_town_joins_total = value_or(pf_town_joins_total, 0) + 1"), m("pf_tj_last = time('now')"),
        {"if": m("pf_tj_found == 1"),
         "then": [{"if": m("value_or(pf_town_named, 0) == 1"), "then": [line("join_house_named")], "else": [line("join_house")]}],
         "else": [line("join_tent")]},
    ], "u = avatar.  They get a house of their own: an empty bed 12-60 tiles from home that no other household has (else a tent at the edge of the place).  The whole family moves in: residents with jobs, defended and defending, but sleeping under their own roof."),
    eoc("PF_TOWN_house_try", [
        {"u_location_variable": g("pf_tj_try"), "furniture": "f_bed", "target_min_radius": 10, "target_max_radius": 50,
         "true_eocs": [{"id": "PF_TOWN_house_check", "effect": house_free + [
             {"if": m("pf_tj_ok == 1"), "then": [m("pf_tj_found = 1"), {"copy_var": g("pf_tj_try"), "target_var": g("pf_tj_house")}]}]}]},
    ], "u = avatar (home is within 30 tiles).  One look for an empty house: a bed 10-50 tiles away, 12-60 from home, and not within 8 tiles of another household's."),
    eoc("PF_TOWN_join_band", [m("pf_tj_off = value_or(u_pf_online, 0) == 0")] + [
        {"if": {"not": {"compare_string": [{"u_val": "pf_member_%d" % k}, "none"]}}, "then": [by_uid(SETTLE, {"u_val": "pf_member_%d" % k})]}
        for k in range(5)] + [{"run_eocs": SETTLE},
        m("pf_m_str_in = 70"), {"run_eocs": "PF_MK_welcomed", "alpha_talker": "avatar", "beta_talker": "u"}],
        "u = the family's leader (by unique id).  Everyone moves in.  If the family was out of range (A-Life keeps it as data then, its bodies parked wherever they were), they're placed at their new house: nothing would ever walk them there."),
    eoc("PF_TOWN_settle_one", [
        {"copy_var": g("pf_tj_house"), "target_var": {"u_val": "pf_house"}},
        m("u_pf_household = pf_tj_hh"), m("u_pf_joining = 0"), m("u_pf_visiting = 0"), m("u_pf_town = 1"),
        {"if": m("pf_tj_off == 1"), "then": [{"copy_var": {"u_val": "pf_house"}, "target_var": {"u_val": "pf_tp"}},
                {"location_variable_adjust": {"u_val": "pf_tp"}, "x_adjust": m("rand(4) - 2"), "y_adjust": m("rand(4) - 2")},
                {"u_teleport": {"u_val": "pf_tp"}, "force_safe": True}]},
    ], "u = someone moving to the town: their own house (before PF_HOME_join_one, whose walk home then goes there)."),
    eoc("PF_TOWN_bring_band", [
        {"if": {"not": {"compare_string": [{"u_val": "pf_member_%d" % k}, "none"]}}, "then": [by_uid(["PF_TOWN_bring_one"], {"u_val": "pf_member_%d" % k})]}
        for k in range(5)] + [{"run_eocs": "PF_TOWN_bring_one"}],
        "u = a household's leader (by unique id): everyone is placed at their house (repair, Town lab)."),
    eoc("PF_TOWN_bring_one", [{"if": m("has_var(u_pf_house)"), "then": [{"copy_var": {"u_val": "pf_house"}, "target_var": {"u_val": "pf_tp"}},
                {"location_variable_adjust": {"u_val": "pf_tp"}, "x_adjust": m("rand(4) - 2"), "y_adjust": m("rand(4) - 2")},
                {"u_teleport": {"u_val": "pf_tp"}, "force_safe": True}]}]),
    eoc("PF_TOWN_join_no", [by_uid(["PF_TOWN_join_back"], g("pf_tj_lead")), line("join_no")],
        "u = avatar.  You said no: they go back home."),
    eoc("PF_TOWN_join_back", [
        m("u_pf_joining = 0"),
        {"copy_var": {"u_val": "pf_home"}, "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": {"u_val": "pf_home"}, "target_var": {"u_val": "pf_wp_b"}},
        {"copy_var": {"u_val": "pf_home"}, "target_var": {"u_val": "pf_goal"}},
    ], "u = the family's leader: back to their own place."),
]

# ---------------------------------------------------------------- the watch (a rota, two shifts, posts; the watch raises the Horn)
def names_list(s, k_max=4):
    """set_string_var effects that join pf_wt_nm_<s>_1.. into pf_wt_list_<s> ('A', 'A and B', 'A, B and C', ...)."""
    out = []
    for n in range(1, k_max + 1):
        parts = [f"<global_val:pf_wt_nm_{s}_{j}>" for j in range(1, n + 1)]
        text = parts[0] if n == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
        out.append({"if": m(f"pf_wt_n_{s} == {n}"), "then": [{"set_string_var": text, "target_var": g(f"pf_wt_list_{s}"), "parse_tags": True}]})
    return out
def pick(s, j):
    """Effects: choose the watcher for shift s, post j (if this night needs that many)."""
    return [{"if": m(f"pf_wt_k >= {j}"), "then": [
        m("pf_wt_best = -1"), m(f"pf_wt_s = {s}"), m(f"pf_wt_j = {j}"),
        {"u_run_npc_eocs": ["PF_TWATCH_cand"], "local": True, "npc_range": 60},
        {"if": m("pf_wt_best >= 0"), "then": [{"run_eocs": "PF_TWATCH_assign", "alpha_talker": g("pf_wt_who")}]}]}]
store_name = [{"if": {"and": [m(f"pf_wt_s == {s}"), m(f"pf_wt_n_{s} == {j}")]}, "then": [name_into(f"pf_wt_nm_{s}_{j}"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g(f"pf_wt_uid_{s}_{j}")}]}
              for s in (1, 2) for j in range(1, 5)]
TO_POST = [{"u_location_variable": {"u_val": "pf_post"}, "min_radius": 8, "max_radius": 14, "outdoor_only": True, "passable_only": True},
           {"copy_var": {"u_val": "pf_post"}, "target_var": {"u_val": "pf_walk_to"}}, {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]
GO_ON = [{"u_lose_effect": "sleep"}, {"u_lose_effect": "lying_down"}, m("u_pf_on_watch = 1")] + TO_POST
files["watch.json"] = [
    eoc("PF_TWATCH_tick", [
        m(f"pf_wt_tn = {NIGHT}"),
        {"if": m("value_or(pf_wt_night, -1) != pf_wt_tn"), "then": [m("pf_wt_night = pf_wt_tn"), m("pf_wt_phase = 0"), m("pf_wt_on = 0")]},
        {"u_location_variable": g("pf_wt_av")},
        {"if": m("distance(pf_wt_av, pf_home_loc) <= 60"), "then": [
            {"if": {"and": [m("pf_wt_phase == 0"), {"or": [m(f"{HOUR} >= 22"), m(f"{HOUR} < 1")]}]}, "then": [{"run_eocs": "PF_TWATCH_post"}]},
            {"if": {"and": [m("pf_wt_phase == 1"), m(f"{HOUR} >= 2"), m(f"{HOUR} < 12")]}, "then": [{"run_eocs": "PF_TWATCH_change"}]},
            {"if": {"and": [m("pf_wt_phase == 2"), m(f"{HOUR} >= 6"), m(f"{HOUR} < 12")]}, "then": [{"run_eocs": "PF_TWATCH_dawn"}]},
            {"if": {"and": [m("pf_wt_on == 1"), m("value_or(pf_horn_active, 0) == 0")]}, "then": [
                {"u_run_npc_eocs": [{"id": "PF_TWATCH_keep", "condition": ON_WATCH, "effect": [
                    {"u_location_variable": {"u_val": "pf_pos"}},
                    {"if": {"u_has_effect": "sleep"}, "then": [{"u_lose_effect": "sleep"}, {"u_lose_effect": "lying_down"}]},
                    {"if": m("distance(u_pf_pos, u_pf_post) > 2"), "then": [{"copy_var": {"u_val": "pf_post"}, "target_var": {"u_val": "pf_walk_to"}}, {"u_set_guard_pos": {"u_val": "pf_walk_to"}}]}]}],
                 "local": True, "npc_range": 60}]}]},
    ], "Every 10 minutes, when you're within 60 tiles of home: at 22:00 the watch goes up (once at least 3 grown-ups live here), at 02:00 it changes, at 06:00 it comes in.  Between times the watchers keep to their posts (not while the Horn is sounding: then they fight).",
        recurrence="10 minutes", **{"global": True}, condition=m(AT_HOME)),
    eoc("PF_TWATCH_post", [
        m("pf_wt_adults = 0"),
        {"u_run_npc_eocs": [{"id": "PF_TWATCH_count", "condition": {"and": [ADULT, m("value_or(u_pf_resident, 0) == 1")]}, "effect": [m("pf_wt_adults += 1")]}], "local": True, "npc_range": 60},
        {"if": m("pf_wt_adults < 3"), "then": [m("pf_wt_phase = 9")], "else": [
            m("pf_wt_dead0 = value_or(pf_ours_dead_total, 0)"),
            m("pf_wt_k = pf_wt_adults >= 18 ? 4 : (pf_wt_adults >= 12 ? 3 : (pf_wt_adults >= 6 ? 2 : 1))"),
            m("pf_wt_n_1 = 0"), m("pf_wt_n_2 = 0"), m("pf_wt_s = 1")]
            + pick(1, 1) + pick(1, 2) + pick(1, 3) + pick(1, 4) + pick(2, 1) + pick(2, 2) + pick(2, 3) + pick(2, 4)
            + names_list(1) + names_list(2) + [
            {"if": m("pf_wt_n_1 == 0"), "then": [m("pf_wt_phase = 9")], "else": [
                m("pf_wt_phase = 1"), m("pf_wt_on = 1"), {"copy_var": g("pf_wt_list_1"), "target_var": g("pf_wt_cur")},
                # full run days 102 and 108: you fell asleep before ten, someone took the watch for you, then the town watch went
                # up, and at dawn "Easter Godfrey kept watch through the night" (Mitzi had it, all night).  The town watch takes over.
                m("pf_wt_handed = 0"),
                {"if": m("value_or(pf_watch_active, 0) == 1"), "then": [m("pf_watch_active = 0"), {"copy_var": g("pf_watch_uid"), "target_var": g("pf_watch_last")},
                    # Kinfold day 148: "Mitzi: 'I'll take the watch.'" and then "Tonight's watch: Beau Blair, all night." with
                    # nothing between; say the handover
                    {"set_string_var": "pf_name_<global_val:pf_watch_uid>", "target_var": ctx("whn"), "parse_tags": True},
                    {"copy_var": {"var_val": "whn"}, "target_var": g("pf_wt_hand")}, m("pf_wt_handed = 1")]},
                {"if": m(CALM), "then": [{"if": m("pf_wt_n_2 > 0"),
                    "then": [{"if": m("rand(1) == 0"), "then": [line("watch_rota")], "else": [line("watch_rota_b")]}],
                    "else": [line("watch_rota_one")]},
                 {"if": m("pf_wt_handed == 1"), "then": [line("watch_handover")]},
                 {"if": m("value_or(pf_law_watch, 0) == 1"), "then": [{"run_eocs": "PF_SAY_keep", "alpha_talker": "avatar", "variables": {"line": "law_watch_note"}}]}]}]}]},
    ], "u = avatar.  Tonight's rota: one watcher per post (1 post for 3-5 grown-ups, 2 for 6+, 3 for 12+, 4 for 18+), two shifts.  Guards first, nobody two nights running if it can be helped, and the second on a shift is someone who gets on with the first (their own warmth, half of it).  The first shift goes to their posts now; the second sleeps until two."),
    eoc("PF_TWATCH_cand", [
        m("_s = 50 + rand(20) + (value_or(u_pf_role, 0) == 2) * 30 * (value_or(pf_law_watch, 0) == 0)"),
        m(f"_s -= (value_or(u_pf_watch_night, -9) == {NIGHT} - 1) * (value_or(pf_law_watch, 0) == 1 ? 80 : 40) + (value_or(u_pf_watch_night, -9) == {NIGHT} - 2) * 15"),
        {"if": m("pf_wt_j > 1"), "then": [
            {"if": m("pf_wt_s == 1"), "then": [{"copy_var": g("pf_wt_uid_1_1"), "target_var": g("pf_m_other")}], "else": [{"copy_var": g("pf_wt_uid_2_1"), "target_var": g("pf_m_other")}]},
            {"run_eocs": "PF_VIEW_read"}, m("_s += pf_read_w / 2")]},
        {"if": m("_s > pf_wt_best"), "then": [m("pf_wt_best = _s"), {"u_set_talker": g("pf_wt_who")}]},
    ], "u = a grown-up who lives here, awake enough to stand a watch (not heavily pregnant, not badly hurt, not already on tonight).",
        condition={"and": [ADULT, m("value_or(u_pf_resident, 0) == 1"), m("has_var(u_pf_uid)"), m(f"value_or(u_pf_watch_night, -1) != {NIGHT}"),
                           {"not": {"u_has_effect": "PF_preg_3"}}, m("u_hp('torso') >= u_hp_max('torso') * 0.6"),
                           # full run day 164: Beau Blair stood the watch on his wedding night.  Newlyweds get the night off.
                           m("(value_or(u_pf_rel_stage, 1) == 3) * (time('now') - value_or(u_pf_stage_since, -999999) < time('1 d')) == 0"),
                           # day 169: Janey had the first watch the night she gave birth.  A mother rests a week, the father a night.
                           m("time('now') - value_or(u_pf_birth_t, -999999) >= time('7 d')"),
                           {"not": {"and": [{"compare_string": [{"u_val": "pf_uid"}, g("pf_last_birth_dad")]},
                                            m("time('now') - value_or(pf_last_birth_t, -999999) < time('1 d')")]}}]}),
    eoc("PF_TWATCH_assign", [
        m(f"u_pf_watch_night = {NIGHT}"), m("u_pf_watch_shift = pf_wt_s"), m("u_pf_on_watch = 0"),
        {"if": m("pf_wt_s == 1"), "then": [m("pf_wt_n_1 += 1")], "else": [m("pf_wt_n_2 += 1")]},
    ] + store_name + [
        {"if": m("pf_wt_s == 1"), "then": GO_ON},
    ], "u = tonight's watcher (same turn as the pick)."),
    eoc("PF_TWATCH_change", [
        m("pf_wt_phase = 2"),
        # full run day 99: the second shift was picked at 22:00; two of them died in the siege at midnight and the 02:00 line
        # still sent them "out to the posts".  The second shift is whoever of them is still here, and the names are rebuilt.
        m("pf_wt_s = 2"), m("pf_wt_n_2 = 0"),
        {"u_run_npc_eocs": [{"id": "PF_TWATCH_wake2", "condition": {"and": [m(f"value_or(u_pf_watch_night, -1) == {NIGHT}"), m("value_or(u_pf_watch_shift, 0) == 2"),
                                                                            m("u_hp('torso') > 0"), m("u_hp('head') > 0")]},
                             "effect": [m("pf_wt_n_2 += 1")] + store_name + GO_ON}], "local": True, "npc_range": 60},
        {"if": m("pf_wt_n_2 > 0"), "then": names_list(2) + [
            {"u_run_npc_eocs": [{"id": "PF_TWATCH_relieve", "condition": {"and": [ON_WATCH, m("value_or(u_pf_watch_shift, 0) == 1")]},
                                 "effect": [m("u_pf_on_watch = 0"), m("u_pf_bed_night = -1")]}], "local": True, "npc_range": 60},
            {"copy_var": g("pf_wt_list_2"), "target_var": g("pf_wt_cur")},
            {"if": m(CALM), "then": [{"if": m(f"value_or(pf_wt_seen_night, -1) == {NIGHT}"), "then": [line("watch_change_seen")],
                                     "else": [{"if": m("rand(1) == 0"), "then": [line("watch_change")], "else": [line("watch_change_b")]}]}]}]},
    ], "u = avatar.  Two o'clock: the first shift wakes the second and goes to bed (a fresh bed claim).  With nobody on the second shift, the first stays out till dawn."),
    eoc("PF_TWATCH_dawn", [
        m("pf_wt_phase = 3"), m("pf_wt_on = 0"), {"u_location_variable": g("pf_wt_av")},
        {"u_run_npc_eocs": [{"id": "PF_TWATCH_in", "condition": {"and": [m(f"value_or(u_pf_watch_night, -1) == {NIGHT}"), m("has_var(u_pf_uid)")]}, "effect": [
            m("u_pf_on_watch = 0"), m("u_pf_watches = value_or(u_pf_watches, 0) + 1"),
            {"u_set_talker": g("pf_wt_cur_w")}, {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_wt_cur_uid")}, m("pf_wt_cur_shift = u_pf_watch_shift"), m("pf_wt_pairs = 0"),
            {"u_run_npc_eocs": [{"id": "PF_TWATCH_partner", "condition": {"and": [m("pf_wt_pairs == 0"), m(f"value_or(u_pf_watch_night, -1) == {NIGHT}"),
                                                                                   m("value_or(u_pf_watch_shift, 0) == pf_wt_cur_shift"), {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_wt_cur_uid")]}}]},
                                 "effect": [m("pf_wt_pairs = 1"), m("pf_m_str_in = 30"), {"run_eocs": "PF_MK_watch_covered", "alpha_talker": g("pf_wt_cur_w"), "beta_talker": "u"}]}],
             "local": True, "npc_range": 60},
            {"if": m("distance(pf_wt_av, pf_home_loc) <= 30"), "then": [m("pf_m_str_in = 20"), {"run_eocs": "PF_MK_watch_covered", "beta_talker": "avatar"}]}]}],
         "local": True, "npc_range": 60},
        m("pf_wt_nights_total = value_or(pf_wt_nights_total, 0) + 1"),
        {"if": m("pf_wt_n_2 > 0"), "then": [{"copy_var": g("pf_wt_list_2"), "target_var": g("pf_wt_cur")}], "else": [{"copy_var": g("pf_wt_list_1"), "target_var": g("pf_wt_cur")}]},
        # full run day 99: "everyone's still here" the morning after four died in the siege; a night with losses says so
        {"if": m("value_or(pf_ours_dead_total, 0) > value_or(pf_wt_dead0, 0)"), "then": [line("watch_loss")], "else": [{"if": m(CALM), "then": [
            {"if": m(f"value_or(pf_wt_seen_night, -1) == {NIGHT}"), "then": [line("watch_held")],
             "else": [m("_q = rand(2)"), {"if": m("_q == value_or(pf_wt_q_last, -1)"), "then": [m("_q = (_q + 1) % 3")]}, m("pf_wt_q_last = _q"),
                      {"if": m("_q == 0"), "then": [line("watch_quiet_0")]}, {"if": m("_q == 1"), "then": [line("watch_quiet_1")]}, {"if": m("_q == 2"), "then": [line("watch_quiet_2")]}]}]}]},
    ], "u = avatar.  Six o'clock: the watch comes in.  Everyone who stood a watch tonight: a shared moment with the one who stood it with them (watch_covered, both ways across a pair), and with you if you slept at home."),
    eoc("PF_TWATCH_spot_tick", [
        m("pf_wt_found = 0"), {"set_string_var": "", "target_var": g("pf_wt_spot")},
        {"u_run_npc_eocs": [{"id": "PF_TWATCH_look", "condition": {"and": [ON_WATCH, {"not": {"u_has_effect": "sleep"}}]}, "effect": [
            m("pf_wt_saw = 0"), {"u_location_variable": g("pf_wt_wpos")},
            {"u_run_monster_eocs": [{"id": "PF_TWATCH_mon", "condition": {"and": [m("pf_wt_saw == 0"), m("u_monsters_nearby('radius': 0) > 0")]},
                                     "effect": [{"u_location_variable": g("pf_wt_mtry")},
                                                {"if": {"line_of_sight": 15, "loc_1": g("pf_wt_wpos"), "loc_2": g("pf_wt_mtry")},
                                                 "then": [m("pf_wt_saw = 1"), {"copy_var": g("pf_wt_mtry"), "target_var": g("pf_wt_seen_mpos")}]}]}],
             "monster_range": 15},
            {"if": {"and": [m("pf_wt_saw == 1"), m("pf_wt_found == 0")]}, "then": [m("pf_wt_found = 1"), name_into("pf_wt_spot")]}]}],
         "local": True, "npc_range": 60},
        {"if": m("pf_wt_found == 1"), "then": [
            m("pf_wt_seen_t = time('now')"), m("pf_horn_last = time('now')"), m(f"pf_wt_seen_night = {NIGHT}"),
            {"copy_var": g("pf_wt_spot"), "target_var": g("pf_wt_hero")},
            {"if": {"and": [m("value_or(pf_horn_active, 0) == 0"), m("value_or(pf_horn_on, 1) == 1")]}, "then": [
                m("pf_wt_sightings_total = value_or(pf_wt_sightings_total, 0) + 1"),
                {"run_eocs": "PF_HORN_alarm", "alpha_talker": "avatar"}]}]},
    ], "Every 2 minutes while the watch is up: each watcher on a post looks out: a hostile monster within 15 tiles in clear line of sight (line_of_sight works at night; monster_must_see failed in the dark, where a zombie's own sight is a few tiles).  The first one to see something raises the Horn, by name; while it's out there the alarm stays up.",
        recurrence="2 minutes", **{"global": True}, condition={"and": [m("value_or(pf_wt_on, 0) == 1"), m(f"value_or(pf_wt_night, -1) == {NIGHT}")]}),
    eoc("PF_TWATCH_menu", [
        {"if": {"and": [m(f"value_or(pf_wt_night, -1) == {NIGHT}"), m("value_or(pf_wt_phase, 0) >= 1"), m("value_or(pf_wt_phase, 0) <= 3")]},
         "then": [{"if": m("pf_wt_n_2 > 0"), "then": [line("watch_menu")], "else": [line("watch_menu_one")]}],
         "else": [line("watch_menu_none")]},
    ], "u = avatar.  Home menu: Tonight's watch.", condition=m(AT_HOME)),
]

L1, L2, WC = "<global_val:pf_wt_list_1>", "<global_val:pf_wt_list_2>", "<global_val:pf_wt_cur>"
LINES.update({
    "status_hh": ("Households: <global_val:pf_tw_hh>.  <global_val:pf_tw_word_cap>.", "info"),
    "join_word": ("Word comes from <global_val:pf_tj_name>'s place: they've packed up everything they own, and they're headed your way.", "info"),
    "join_house": ("<global_val:pf_tj_name> and their family move into the empty house down the way.  There's another lit window tonight.", "good"),
    "join_house_named": (f"<global_val:pf_tj_name> and their family move into the empty house down the way.  {TN} has another lit window tonight.", "good"),
    "join_tent": ("<global_val:pf_tj_name> and their family pitch a tent at the edge of the place, until something better comes along.", "good"),
    "join_no": ("<global_val:pf_tj_name> nods slowly.  \"We understand.\"  They turn the handcart around and head back the way they came.", "bad"),
    "watch_rota": (f"Tonight's watch: {L1} until two, then {L2}.", "info"),
    "watch_rota_b": (f"First watch tonight: {L1}.  Second watch, from two: {L2}.", "info"),
    "watch_handover": ("<global_val:pf_wt_hand> hands the watch over and gets some sleep after all.", "info"),
    "watch_rota_one": (f"Tonight's watch: {L1}, all night.", "info"),
    "watch_change": (f"Two o'clock.  The watch changes hands with a yawn and a 'nothing yet': {L1} to bed, {L2} out to the posts.", "info"),
    "watch_change_b": (f"Second watch: {L2}, shaken awake and out into the dark.  First watch: {L1}, asleep before their boots are off.", "info"),
    "watch_loss": ("The watch comes in at dawn, grey in the face.  Nobody says the names yet.  Somebody puts the coffee on anyway, and nobody drinks it.", "bad"),
    "watch_held": ("The watch comes in at dawn.  <global_val:pf_wt_hero> saw them first last night, and everyone's still here.", "good"),
    "watch_change_seen": (f"Two o'clock.  The watch changes hands, everyone still wired from the scare: {L1} to bed, {L2} out to the posts, eyes on the dark where it came from.", "info"),
    "watch_quiet_0": (f"Dawn.  The night watch comes in stamping their feet: {WC}.  A quiet night.", "good"),
    "watch_quiet_1": ("The watch comes in with the sun.  Nothing moved out there all night but an owl.", "good"),
    "watch_quiet_2": (f"The watch hands in the night ({WC}): quiet.  Somebody's already put the coffee on.", "good"),
    "watch_menu": (f"Tonight's watch: {L1} until two, then {L2}.", "info"),
    "watch_menu_one": (f"Tonight's watch: {L1}, all night.", "info"),
    "watch_menu_none": ("Nobody is on the watch tonight yet.  It goes up at ten, once at least three grown-ups live here.", "info"),
    "watch_sleep": (f"You sleep easy.  On the watch: {WC}.", "good"),
})
files["lines.json"] = [eoc("PF_SAY_town", [{"if": {"compare_string": [ctx("line"), k]}, "then": [say(t, ty)]} for k, (t, ty) in LINES.items()],
                           "u = avatar.  Town lines, picked by the context var 'line'.")]
# How the place is doing: households and word of the place
files["town.json"][1]["effect"] += [
    {"run_eocs": "PF_TOWN_appeal"}, m("pf_tw_hh = 1 + value_or(pf_households_n, 0)"),
    {"if": m("pf_town_appeal < 25"), "then": [{"set_string_var": "Nobody out there has heard of the place", "target_var": g("pf_tw_word_cap")}]},
    {"if": m("(pf_town_appeal >= 25) * (pf_town_appeal < 50)"), "then": [{"set_string_var": "People out there have heard of the place", "target_var": g("pf_tw_word_cap")}]},
    {"if": m("(pf_town_appeal >= 50) * (pf_town_appeal < 75)"), "then": [{"set_string_var": "People out there talk about the place", "target_var": g("pf_tw_word_cap")}]},
    {"if": m("pf_town_appeal >= 75"), "then": [{"set_string_var": "People out there say it's the place to be", "target_var": g("pf_tw_word_cap")}]},
    line("status_hh")]

files["lab_town.json"] += [
    eoc("PF_TL_join", [
        m("pf_tj_force = 1"), m("pf_tj_active = 0"), m("pf_tj_best = -1"), m("pf_town_appeal = 0"), m("pf_wi = 0"),
        {"run_eocs": "PF_TOWN_join_i", "condition": m("pf_wi < value_or(pf_band_n, 0)"), "iterations": 1000},
        m("pf_tj_force = 0"),
        {"if": m("pf_tj_best >= 0"), "then": [by_uid(["PF_TOWN_join_go"], g("pf_tj_lead")), say("[town lab] <global_val:pf_tj_name>'s family is on its way (they walk in like any band; they ask once they're within 25 tiles of home).")],
         "else": [say("[town lab] No settled family out there (World: a family settles in a house nearby).")]}],
        "Town lab: the nearest settled family decides to join now."),
    eoc("PF_TL_join_ask", [
        {"if": m("value_or(pf_tj_active, 0) == 1"), "then": [{"run_eocs": "PF_TOWN_ask"}], "else": [say("[town lab] No family is on its way (use the entry above first).")]}],
        "Town lab: the family on its way asks now, wherever they are."),
    eoc("PF_TL_watch", [m(f"pf_wt_night = {NIGHT}"), m("pf_wt_phase = 0"), {"run_eocs": "PF_TWATCH_post"},
                        {"if": m("pf_wt_phase == 9"), "then": [say("[town lab] Not enough grown-ups (3+) who live here and can stand a watch, within 60 tiles.")]}],
        "Town lab: tonight's watch goes up now (ignores the clock)."),
    eoc("PF_TL_watch_change", [{"if": m("value_or(pf_wt_phase, 0) == 1"), "then": [{"run_eocs": "PF_TWATCH_change"}], "else": [say("[town lab] The first watch isn't up.")]}],
        "Town lab: change of watch now."),
    eoc("PF_TL_watch_dawn", [{"if": {"or": [m("value_or(pf_wt_phase, 0) == 1"), m("value_or(pf_wt_phase, 0) == 2")]}, "then": [{"run_eocs": "PF_TWATCH_dawn"}], "else": [say("[town lab] No watch is up.")]}],
        "Town lab: the watch comes in now."),
    eoc("PF_TL_watch_spot", [
        m("pf_hl_got = 0"),
        {"u_run_npc_eocs": [{"id": "PF_TL_watcher_pos", "condition": {"and": [ON_WATCH, m("pf_hl_got == 0")]},
                             "effect": [m("pf_hl_got = 1"), {"u_location_variable": g("pf_hl_wpos")}, {"location_variable_adjust": g("pf_hl_wpos"), "x_adjust": 7}]}], "local": True, "npc_range": 60},
        {"if": m("pf_hl_got == 1"), "then": [{"u_spawn_monster": "mon_zombie", "real_count": 1, "target_var": g("pf_hl_wpos"), "min_radius": 0, "max_radius": 1},
                                             say("[town lab] A zombie, 7 tiles east of a watcher.")],
         "else": [say("[town lab] Nobody is on a post.")]}],
        "Town lab: a zombie near someone on the watch."),
    eoc("PF_TL_bring", [{"if": m("value_or(pf_households_n, 0) > 0"), "then": [by_uid(["PF_TOWN_bring_band"], g("pf_tj_lead")), say("[town lab] The newest household is at its house.")],
                         "else": [say("[town lab] No family has joined yet.")]}],
        "Town lab: the newest household is placed at its house (repair for a family that joined out of range before the fix)."),
    eoc("PF_TL_stats3", [
        {"run_eocs": "PF_TOWN_appeal"},
        m("pf_hs_a = 1 + value_or(pf_households_n, 0)"), m("pf_hs_b = value_or(pf_town_joins_total, 0)"), m("pf_hs_c = value_or(pf_wt_nights_total, 0)"),
        m("pf_hs_d = value_or(pf_wt_sightings_total, 0)"), m("pf_hs_e = pf_town_appeal"), m("pf_hs_f = value_or(pf_wt_phase, -1)"),
        say("[town lab] households <global_val:pf_hs_a>, families joined <global_val:pf_hs_b>, nights watched <global_val:pf_hs_c>, sightings <global_val:pf_hs_d>, draw <global_val:pf_hs_e>, watch phase <global_val:pf_hs_f>.")]),
]

for fname, data in files.items():
    json.dump(data, open(os.path.join(OUT, fname), "w", encoding="utf-8", newline="\n"), indent=2)
print("town written:", {k: len(v) for k, v in files.items()})
