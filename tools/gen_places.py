"""v0.9 Their own lives: generates mods/PeopleFirst/places/ (travel.json, places.json, movein.json).

The user, 2026-10-17: "How can the mod ever be about npc autonomy if they never settle on their own and make their own
group home?  If the only time the player feels like they're surrounded by proper humans is when he invites them in his
home, doesn't that mean he has to become the leader in some sense?  Could he not simply ask to be a band member with
them and follow them to their base?"

1. Travel with a band (travel.json).  "Ask to travel with them": you go where their leader goes.  The band waits when you
   fall behind (alife.json PF_ALIFE_online_step reads the leader's u_pf_tv_player), shares its supper with you, and the
   evening fire and the night watch already gather whoever is near you.  "Part ways with them" leaves a map mark.
2. Places of their own (places.json).  A family that settles founds a named place, or joins one within 8 map tiles;
   bands on the road drift into places within 10 (families settle there, hunters hunt out of them); a place with nobody
   left is abandoned.  Places are data (pf_pl_<k>_*); their people are ordinary A-Life bands living around the spot, so
   when you get there the place is full of real people.  You find a place by walking into it, or someone from it tells you.
3. Live at their place (movein.json).  "Ask to live with them" (someone settled, or from a place): you move in.  Their
   home (the place) becomes yours, every household there joins as a household of the town (v0.5 houses), and their
   leader is chief from day one (v0.6).

Usage:  python tools/gen_places.py mods/PeopleFirst
"""
import json, os, sys

ROOT = sys.argv[1]
OUT = os.path.join(ROOT, "places")


def m(e): return {"math": [e]}
def g(n): return {"global_val": n}
def ctx(n): return {"context_val": n}
def say(text, t="info"): return {"u_message": text, "type": t}
def setg(var, text, parse=False):
    o = {"set_string_var": text, "target_var": g(var)}
    if parse: o["parse_tags"] = True
    return o
def by_uid(eocs, uid): return {"u_run_npc_eocs": eocs, "unique_ids": [uid], "local": False}
def eoc(id_, effect, comment=None, condition=None, **extra):
    o = {"type": "effect_on_condition", "id": id_}
    if comment: o["//"] = comment
    o.update(extra)
    if condition: o["condition"] = condition
    o["effect"] = effect
    return o
def compass(dx, dy, out):
    """Effects: a compass word (north, southeast...) for an offset, into global `out` (y grows southward).  As gen_hearts."""
    return [setg(out + "_ns", ""), setg(out + "_ew", ""),
            {"if": m(f"abs({dy}) * 2 >= abs({dx})"), "then": [
                {"if": m(f"{dy} < 0"), "then": [setg(out + "_ns", "north")], "else": [setg(out + "_ns", "south")]}]},
            {"if": m(f"abs({dx}) * 2 >= abs({dy})"), "then": [
                {"if": m(f"{dx} < 0"), "then": [setg(out + "_ew", "west")], "else": [setg(out + "_ew", "east")]}]},
            setg(out, f"<global_val:{out}_ns><global_val:{out}_ew>", True)]
def roster_loop(eoc_id, per_leader, comment):
    """An EOC that visits every living band's leader (the roster pf_slot_<i>) with per_leader (u = the leader)."""
    return [eoc(eoc_id, [m("pf_pl_i = 0"), {"run_eocs": eoc_id + "_i", "condition": m("pf_pl_i < value_or(pf_band_n, 0)"), "iterations": 1000}], comment),
            eoc(eoc_id + "_i", [
                {"set_string_var": "pf_slot_<global_val:pf_pl_i>", "target_var": ctx("ref"), "parse_tags": True},
                {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [by_uid([eoc_id + "_one"], {"var_val": "ref"})]},
                m("pf_pl_i += 1")]),
            eoc(eoc_id + "_one", per_leader, condition=m("value_or(u_pf_is_leader, 0) == 1"))]

TODAY = "floor(time('now') / time('1 d'))"
HOUR = "time_since('midnight', 'unit': 'hours')"
MAXP = 6             # places in the world at once
MAXBANDS = 5         # households (bands) a place holds
FOUND_R = 192        # a family settling within 8 map tiles of a place joins it instead of founding its own
JOIN_R = 240         # a band on the road within 10 map tiles of a place may drift into it
NAMES = ["Cedar Hollow", "Stillwater", "the Crossing", "Long Meadow", "Ashford", "Haven", "Little Hope", "Tall Pines",
         "Mill Creek", "the Orchard", "Redstone", "Second Chance"]
files = {}

# ============================================================ PLACES
found_join = [
    m("pf_pl_best = -1"), m("pf_pl_bd = 999999"), m("pf_pl_joined = 0"),
    m("pf_pl_r = value_or(pf_pl_join_only, 0) == 1 ? %d : %d" % (JOIN_R, FOUND_R)),
]
for k in range(MAXP):
    found_join.append({"if": {"and": [m(f"value_or(pf_pl_{k}_alive, 0) == 1"), m(f"value_or(pf_pl_{k}_n, 0) < {MAXBANDS}"),
                                      m(f"distance(u_pf_vpos, pf_pl_{k}_at) <= pf_pl_r"), m(f"distance(u_pf_vpos, pf_pl_{k}_at) < pf_pl_bd")]},
                       "then": [m(f"pf_pl_best = {k}"), m(f"pf_pl_bd = distance(u_pf_vpos, pf_pl_{k}_at)")]})
for k in range(MAXP):
    found_join.append({"if": m(f"pf_pl_best == {k}"), "then": [
        m(f"u_pf_place = {k + 1}"), m(f"pf_pl_{k}_n = value_or(pf_pl_{k}_n, 0) + 1"),
        {"copy_var": g(f"pf_pl_{k}_at"), "target_var": {"u_val": "pf_place_at"}},
        {"copy_var": g(f"pf_pl_{k}_name"), "target_var": {"u_val": "pf_place_name"}}]})
found_join += [
    {"if": m("pf_pl_best >= 0"), "then": [
        m("pf_pl_joined = 1"),
        # their own spot near the place's heart (a household of their own)
        {"copy_var": {"u_val": "pf_place_at"}, "target_var": {"u_val": "pf_home"}},
        {"location_variable_adjust": {"u_val": "pf_home"}, "x_adjust": m("(rand(1) * 2 - 1) * (6 + rand(10))"), "y_adjust": m("(rand(1) * 2 - 1) * (6 + rand(10))")},
        {"if": m("value_or(u_pf_task, 0) == 1"),
         # hunters hunt out of the place: two waypoints 2-3 map tiles either side of it
         "then": [m("u_pf_based = 1"),
                  {"copy_var": {"u_val": "pf_place_at"}, "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": {"u_val": "pf_place_at"}, "target_var": {"u_val": "pf_wp_b"}},
                  {"location_variable_adjust": {"u_val": "pf_wp_a"}, "overmap_tile": True, "x_adjust": m("2 + rand(1)"), "y_adjust": m("rand(4) - 2")},
                  {"location_variable_adjust": {"u_val": "pf_wp_b"}, "overmap_tile": True, "x_adjust": m("0 - 2 - rand(1)"), "y_adjust": m("rand(4) - 2")}],
         "else": [m("u_pf_settled = 1"),
                  {"copy_var": {"u_val": "pf_home"}, "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": {"u_val": "pf_home"}, "target_var": {"u_val": "pf_wp_b"}}]},
        {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_goal"}}, m("u_pf_goal_is_b = 0"), m("u_pf_camp_until = 0"),
        m("pf_places_joined_total = value_or(pf_places_joined_total, 0) + 1"),
        {"if": m("(value_or(pf_tv_on, 0) == 1) * (value_or(u_pf_band, -1) == value_or(pf_tv_band, -2))"), "then": [
            setg("pf_pl_say_lead", "<u_name>", True), {"copy_var": {"u_val": "pf_place_name"}, "target_var": g("pf_pl_say_place")},
            {"run_eocs": {"id": "PF_PLACE_tv_join_say", "effect": [say("<global_val:pf_pl_say_lead> says they're done wandering: the band is making its home at <global_val:pf_pl_say_place>, and you're welcome to come.", "good")]},
             "alpha_talker": "avatar"}]}]},
    # nobody near to join: a family founds a place of its own where it settled (pf_home = where it stands)
    {"if": m("(pf_pl_best == -1) * (value_or(pf_pl_join_only, 0) == 0) * (value_or(u_pf_settled, 0) == 1)"), "then": [
        m("pf_pl_free = -1")] + [{"if": m(f"(pf_pl_free == -1) * (value_or(pf_pl_{k}_alive, 0) == 0)"), "then": [m(f"pf_pl_free = {k}")]} for k in range(MAXP)] + [
        {"if": m(f"pf_pl_free == {k}"), "then": [
            m(f"pf_pl_{k}_alive = 1"), m(f"pf_pl_{k}_n = 1"), m(f"pf_pl_{k}_known = 0"), m(f"pf_pl_{k}_since = time('now')"),
            {"copy_var": {"u_val": "pf_home"}, "target_var": g(f"pf_pl_{k}_at")},
            {"copy_var": {"u_val": "pf_uid"}, "target_var": g(f"pf_pl_{k}_lead")}, setg(f"pf_pl_{k}_fname", "<u_name>", True),
            {"switch": m("value_or(pf_pl_names_i, 0) %% %d" % len(NAMES)),
             "cases": [{"case": i, "effect": [setg(f"pf_pl_{k}_name", nm)]} for i, nm in enumerate(NAMES)]},
            m("pf_pl_names_i = value_or(pf_pl_names_i, 0) + 1"),
            m(f"u_pf_place = {k + 1}"),
            {"copy_var": g(f"pf_pl_{k}_at"), "target_var": {"u_val": "pf_place_at"}},
            {"copy_var": g(f"pf_pl_{k}_name"), "target_var": {"u_val": "pf_place_name"}},
            m("pf_places_founded_total = value_or(pf_places_founded_total, 0) + 1")]} for k in range(MAXP)]},
]
# count first; a settled band from before v0.9 then finds or founds its place (which counts it itself)
count_one = [{"if": {"and": [m(f"value_or(u_pf_place, 0) == {k + 1}"), m("(value_or(u_pf_settled, 0) == 1) + (value_or(u_pf_based, 0) == 1) > 0")]},
              "then": [m(f"pf_pl_{k}_n += 1")]} for k in range(MAXP)] + [
    {"if": {"and": [m("value_or(u_pf_settled, 0) == 1"), m("value_or(u_pf_place, 0) == 0")]},
     "then": [m("pf_pl_join_only = 0"), {"run_eocs": "PF_PLACE_found_or_join"}]}]
files["places.json"] = [
    eoc("PF_PLACE_found_or_join", found_join,
        "u = a band's leader, settling now (pf_pl_join_only 0) or on the road near a place (1).  Joins the nearest place with room within 8 map tiles (10 on the road): a household spot near its heart; families settle there, hunters hunt out of it (u_pf_based).  Else a settling family founds a place of its own.  pf_pl_joined = 1 if it joined one."),
] + roster_loop("PF_PLACE_count", count_one, "Counts each place's households (settled or based bands); settled bands from before v0.9 find or found their place.") + [
    eoc("PF_PLACE_tick", [m(f"pf_pl_{k}_n = 0") for k in range(MAXP)] + [{"run_eocs": "PF_PLACE_count"}] + [
        {"if": m(f"(value_or(pf_pl_{k}_alive, 0) == 1) * (pf_pl_{k}_n == 0)"), "then": [
            m(f"pf_pl_{k}_alive = 0"), m("pf_places_abandoned_total = value_or(pf_places_abandoned_total, 0) + 1")]} for k in range(MAXP)],
        "Once a day: how many households each place has; a place with nobody left is abandoned (its slot can hold a new one).",
        recurrence="1 days", **{"global": True}, condition=m("value_or(pf_alife_on, 1) == 1")),
    eoc("PF_PLACE_near_tick", [{"u_location_variable": g("pf_pl_av")}] + [
        {"if": {"and": [m(f"value_or(pf_pl_{k}_alive, 0) == 1"), m(f"value_or(pf_pl_{k}_known, 0) == 0"), m(f"distance(pf_pl_av, pf_pl_{k}_at) <= 45")]}, "then": [
            m(f"pf_pl_{k}_known = 1"),
            {"if": m(f"pf_pl_{k}_n <= 1"),
             "then": [say(f"You come to a place someone has made a home of: <global_val:pf_pl_{k}_name>.  <global_val:pf_pl_{k}_fname> started it.", "good")],
             "else": [m(f"pf_pl_say_n = pf_pl_{k}_n"),
                      say(f"You come to <global_val:pf_pl_{k}_name>: <global_val:pf_pl_say_n> households have made a home here.  <global_val:pf_pl_{k}_fname> started it.", "good")]}]}
        for k in range(MAXP)],
        "Every 10 minutes: walking into a place you didn't know (45 tiles of its heart) introduces it, and it goes on Where to find people.",
        recurrence="10 minutes", **{"global": True},
        condition=m(" + ".join(f"value_or(pf_pl_{k}_alive, 0)" for k in range(MAXP)) + " > 0")),
    eoc("PF_PLACE_list_known", [{"u_location_variable": g("pf_pl_av")}, m("pf_pl_shown = 0")] + [
        {"if": {"and": [m(f"value_or(pf_pl_{k}_alive, 0) == 1"), m(f"value_or(pf_pl_{k}_known, 0) == 1")]}, "then": [
            m("pf_pl_shown += 1"), m(f"pf_pl_say_n = pf_pl_{k}_n"),
            m(f"pf_pl_dx = pf_pl_{k}_at.x - pf_pl_av.x"), m(f"pf_pl_dy = pf_pl_{k}_at.y - pf_pl_av.y"),
            m("pf_pl_mt = floor((max(abs(pf_pl_dx), abs(pf_pl_dy)) + 12) / 24)")] + compass("pf_pl_dx", "pf_pl_dy", "pf_pl_dir") + [
            setg("pf_pl_hh", "<global_val:pf_pl_say_n> households", True),
            {"if": m("pf_pl_say_n == 1"), "then": [setg("pf_pl_hh", "one household")]},
            {"if": m("pf_pl_mt < 2"),
             "then": [say(f"<global_val:pf_pl_{k}_name>, a place people made: right here, <global_val:pf_pl_hh>.")],
             "else": [say(f"<global_val:pf_pl_{k}_name>, a place people made: about <global_val:pf_pl_mt> map tiles <global_val:pf_pl_dir> of here, <global_val:pf_pl_hh>.")]}]}
        for k in range(MAXP)],
        "u = you (Where to find people).  The places people made that you know of, with which way and how many households."),
]

# ============================================================ TRAVEL WITH A BAND
files["travel.json"] = [
    eoc("PF_TRAVEL_ask", [
        m("pf_bd_ok = 0"), {"run_eocs": "PF_PM_bond_read", "alpha_talker": "npc"},
        # a smaller thing to ask than living together: warmth 20 and trust 10 (the meter's third step or so)
        m("pf_tv_yes = (pf_bd_ok == 1) * (pf_read_w >= 20) * (pf_read_t >= 10)"),
        {"if": m("pf_tv_yes == 0"),
         "then": [say("<npc_name> looks you over.  \"We don't take on people we don't know.  Eat with us a few times first.\""),
                  {"if": m("pf_bd_ok == 1"), "then": [say("<global_val:pf_bd_bar> <global_val:pf_bd_word>  <global_val:pf_bd_hint>")]}],
         "else": [m("pf_wh_ok = 0"), {"run_eocs": "PF_WHERE_get_lead", "alpha_talker": "npc"},
                  {"if": m("pf_wh_ok == 1"), "then": [
                      by_uid(["PF_TRAVEL_lead_on"], g("pf_wh_lead")),
                      {"copy_var": g("pf_wh_lead"), "target_var": g("pf_tv_lead")},
                      m("pf_tv_on = 1"), m("pf_tv_since = time('now')"), m("pf_tv_seen = time('now')"), m("pf_tv_day3 = 0"), m("pf_tv_wait_t = 0"),
                      m("pf_tv_total = value_or(pf_tv_total, 0) + 1"),
                      m("pf_m_str_in = 50"), {"run_eocs": "PF_MK_welcomed", "alpha_talker": "npc", "beta_talker": "avatar"},
                      say("<npc_name> looks at the others, then back at you.  \"Keep up, and pull your weight.\"  You travel with <global_val:pf_tv_name>'s band now: where they go, you go.", "good"),
                      say("They lead.  When you want to go your own way, tell one of them (People nearby: Part ways with them).")]}]},
    ], "u = you, npc = someone in a band.  They answer from their own view of you (warmth 20 and trust 10).  Yes: you travel with the band; its leader decides where."),
    eoc("PF_TRAVEL_lead_on", [
        m("u_pf_tv_player = 1"), setg("pf_tv_name", "<u_name>", True),
        m("pf_tv_band = value_or(u_pf_band, 0)"), m("pf_tv_slot = value_or(u_pf_band, 1) - 1"),
    ], "u = the band's leader.  Marks the band as the one you travel with (alife.json: it waits for you)."),
    eoc("PF_TRAVEL_end", [
        m("pf_tv_on = 0"),
        {"set_string_var": "pf_slot_<global_val:pf_tv_slot>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [
            by_uid([{"id": "PF_TRAVEL_lead_off", "effect": [m("u_pf_tv_player = 0")]}], {"var_val": "ref"})]},
    ], "u = you.  You no longer travel with the band."),
    eoc("PF_TRAVEL_part", [
        say("You tell <npc_name> you're going your own way.  \"You know where to find us.\""),
        {"run_eocs": "PF_TRAVEL_end"},
        m("pf_wh_auto = 0"), {"run_eocs": "PF_WHERE_ask"},
    ], "u = you, npc = someone in the band you travel with.  You leave; they tell you where they'll be (a map mark)."),
    eoc("PF_TRAVEL_tick", [
        {"set_string_var": "pf_slot_<global_val:pf_tv_slot>", "target_var": ctx("ref"), "parse_tags": True},
        {"if": {"compare_string": [{"var_val": "ref"}, "none"]},
         "then": [m("pf_tv_on = 0"), say("<global_val:pf_tv_name>'s band is no more.  You're on your own again.", "bad")],
         "else": [
             # the slot holds the band's current leader (a new one after a death)
             {"copy_var": {"var_val": "ref"}, "target_var": g("pf_tv_lead")},
             m("pf_tv_lon = 0"), by_uid(["PF_TRAVEL_lead_read"], g("pf_tv_lead")),
             {"if": m("pf_tv_lon == 1"),
              "then": [
                  m("pf_tv_seen = time('now')"), {"u_location_variable": g("pf_tv_av")},
                  m("pf_tv_d = distance(pf_tv_av, pf_tv_lpos)"),
                  {"if": {"and": [m("pf_tv_d > 15"), m(f"({HOUR} >= 6) * ({HOUR} < 21)"), m("time('now') - value_or(pf_tv_wait_t, 0) >= time('30 m')")]},
                   "then": [m("pf_tv_wait_t = time('now')"), say("<global_val:pf_tv_name>'s band stops and waits for you to catch up.")]},
                  {"if": {"and": [m(f"({HOUR} >= 18) * ({HOUR} < 23)"), m(f"value_or(pf_tv_supper_day, -1) != {TODAY}"), m("pf_tv_d <= 30")]},
                   "then": [{"run_eocs": "PF_TRAVEL_supper"}]}],
              "else": [{"if": m("time('now') - value_or(pf_tv_seen, 0) > time('6 h')"), "then": [
                  {"run_eocs": "PF_TRAVEL_end"},
                  say("You've lost <global_val:pf_tv_name>'s band.  Word along the road might turn them up again (People you know).", "bad")]}]},
             {"if": m("(value_or(pf_tv_on, 0) == 1) * (value_or(pf_tv_day3, 0) == 0) * (time('now') - pf_tv_since >= time('3 d'))"), "then": [
                 m("pf_tv_day3 = 1"), say("Three days on the road with <global_val:pf_tv_name>'s band.  Nobody in it counts you as a stranger anymore.", "good")]}]},
    ], "Every 5 minutes while you travel with a band: the band waits if you fall behind, shares supper in the evening, and if you've lost it for 6 hours you're on your own again.",
        recurrence="5 minutes", **{"global": True}, condition=m("value_or(pf_tv_on, 0) == 1")),
    eoc("PF_TRAVEL_lead_read", [
        m("u_pf_tv_player = 1"), setg("pf_tv_name", "<u_name>", True), m("pf_tv_hunt = value_or(u_pf_task, 0)"),
        {"if": m("value_or(u_pf_online, 0) == 1"), "then": [m("pf_tv_lon = 1"), {"u_location_variable": g("pf_tv_lpos")}]},
    ], "u = the band's leader.  Reads its position only while it's on-screen (loaded: cheap)."),
    eoc("PF_TRAVEL_supper", [
        m(f"pf_tv_supper_day = {TODAY}"),
        {"if": m("pf_tv_hunt == 1"),
         "then": [{"u_spawn_item": "meat_cooked", "suppress_message": True},
                  say("<global_val:pf_tv_name>'s band shares out what they hunted today, and there's a portion for you.", "good")],
         "else": [{"u_spawn_item": "pemmican", "suppress_message": True},
                  say("<global_val:pf_tv_name>'s band shares its supper with you.", "good")]},
        {"u_run_npc_eocs": [{"id": "PF_TRAVEL_supper_one",
                             "condition": {"and": [m("value_or(u_pf_band, 0) == pf_tv_band"), m("value_or(u_pf_resident, 0) == 0")]},
                             "effect": [m("pf_m_str_in = 35"), {"run_eocs": "PF_MK_meal_shared", "beta_talker": "avatar"}]}],
         "local": True, "npc_range": 25},
    ], "u = you, travelling with a band, in the evening.  Once a day: something to eat in your hands, and a meal shared with each of them nearby."),
]

# ============================================================ LIVE AT THEIR PLACE
HOUSES = 8   # as gen_town (pf_house_0..7)
store_house = [{"if": m(f"pf_households_n == {k}"), "then": [{"copy_var": g("pf_tj_house"), "target_var": g(f"pf_house_{k}")}]} for k in range(HOUSES)]
gather_one = [{"if": {"and": [m("pf_mi_place > 0"), m("value_or(u_pf_place, 0) == pf_mi_place"), m("pf_mi_n < 6"),
                              m("(value_or(u_pf_settled, 0) == 1) + (value_or(u_pf_based, 0) == 1) > 0")]},
               "then": [m("pf_mi_n += 1")] + [{"if": m(f"pf_mi_n == {j + 1}"), "then": [{"copy_var": {"u_val": "pf_uid"}, "target_var": g(f"pf_mi_l_{j}")}]} for j in range(6)]}]
join_bands = []
for j in range(6):
    join_bands.append({"if": m(f"pf_mi_n > {j}"), "then": [
        {"copy_var": g(f"pf_mi_l_{j}"), "target_var": g("pf_inv_lead")},
        by_uid([{"id": f"PF_PLACE_house_{j}", "effect": [{"copy_var": {"u_val": "pf_home"}, "target_var": g("pf_tj_house")}]}], g(f"pf_mi_l_{j}")),
        m("pf_hm_i = 0"), {"run_eocs": "PF_HOME_unroster_i", "condition": m("pf_hm_i < pf_band_n"), "iterations": 1000},
    ] + store_house + [
        m("pf_households_n = value_or(pf_households_n, 0) + 1"), m("pf_tj_hh = pf_households_n"),
        by_uid(["PF_TOWN_join_band"], g(f"pf_mi_l_{j}"))]})
files["movein.json"] = [
    eoc("PF_PLACE_move_in", [
        {"if": m("(value_or(pf_home_set, 0) == 1) * (value_or(pf_residents_n, 0) > 0)"),
         "then": [say("You have people of your own at home.  You can't just walk out on them.")],
         "else": [
             m("pf_bd_ok = 0"), {"run_eocs": "PF_PM_bond_read", "alpha_talker": "npc"},
             {"if": m("(pf_bd_ok == 1) * (pf_bd_ready == 1) == 0"),
              "then": [say("<npc_name> glances at the others.  \"We'd have to know you better first.\""),
                       {"if": m("pf_bd_ok == 1"), "then": [say("<global_val:pf_bd_bar> <global_val:pf_bd_word>  <global_val:pf_bd_hint>")]}],
              "else": [{"run_eocs": "PF_PLACE_move_in_yes"}]}]},
    ], "u = you, npc = someone settled (or from a place).  They answer as they would to living with you (warmth 35 and trust 25, or 50 and 15).  You can't leave a household of your own behind."),
    eoc("PF_PLACE_move_in_yes", [
        m("pf_wh_ok = 0"), {"run_eocs": "PF_WHERE_get_lead", "alpha_talker": "npc"},
        m("pf_mi_n = 0"), m("pf_mi_place = 0"),
        by_uid(["PF_PLACE_host_read"], g("pf_wh_lead")),
        m("pf_mi_old = value_or(pf_home_set, 0)"),
        {"copy_var": g("pf_mi_home"), "target_var": g("pf_home_loc")}, m("pf_home_set = 1"), m("pf_home_since = time('now')"),
        {"run_eocs": "PF_STORES_ensure"},
        # everyone who lives at the place comes with it: each band a household with its own house (v0.5)
        {"if": m("pf_mi_place > 0"), "then": [{"run_eocs": "PF_MI_gather"}],
         "else": [m("pf_mi_n = 1"), {"copy_var": g("pf_wh_lead"), "target_var": g("pf_mi_l_0")}]},
    ] + join_bands + [
        # their leader runs the place (v0.6 chief); the place keeps its name
        m("pf_chief_set = 1"), {"copy_var": g("pf_wh_lead"), "target_var": g("pf_chief_uid")}, {"copy_var": g("pf_mi_lname"), "target_var": g("pf_chief_name")},
        {"if": m("value_or(pf_town_named, 0) == 0"), "then": [{"copy_var": g("pf_mi_pname"), "target_var": g("pf_town_name")}, m("pf_town_named = 1")]},
    ] + [{"if": m(f"pf_mi_place == {k + 1}"), "then": [m(f"pf_pl_{k}_alive = 0"), m(f"pf_pl_{k}_yours = 1")]} for k in range(MAXP)] + [
        {"if": m("value_or(pf_tv_on, 0) == 1"), "then": [m("pf_tv_on = 0")]},
        m("pf_home_host = 1"), m("pf_moved_in_total = value_or(pf_moved_in_total, 0) + 1"),
        m("pf_m_str_in = 70"), {"run_eocs": "PF_MK_welcomed", "alpha_talker": "npc", "beta_talker": "avatar"},
        say("<global_val:pf_mi_lname> shows you a corner that's yours.  \"You pull your weight, and we look after you.\"  You live at <global_val:pf_mi_pname> now, and <global_val:pf_mi_lname> runs the place.", "good"),
        {"if": m("pf_mi_old == 1"), "then": [say("The old place isn't home anymore.")]},
    ], "u = you, npc = the one who said yes.  Home becomes their place; its people become the town's households; their leader is chief."),
    eoc("PF_PLACE_host_read", [
        setg("pf_mi_lname", "<u_name>", True), setg("pf_mi_pname", "<u_name>'s place", True),
        m("pf_mi_place = value_or(u_pf_place, 0)"),
        {"if": m("has_var(u_pf_home)"), "then": [{"copy_var": {"u_val": "pf_home"}, "target_var": g("pf_mi_home")}],
         "else": [{"copy_var": {"u_val": "pf_vpos"}, "target_var": g("pf_mi_home")}]},
        {"if": m("pf_mi_place > 0"), "then": [{"copy_var": {"u_val": "pf_place_at"}, "target_var": g("pf_mi_home")},
                                             {"copy_var": {"u_val": "pf_place_name"}, "target_var": g("pf_mi_pname")}]},
    ], "u = the host band's leader: where home will be, what it's called, and whether it's a place."),
] + roster_loop("PF_MI_gather", gather_one, "Every band of the place you're moving into (up to 6), into pf_mi_l_<j>.")

# ============================================================ PLACES LAB (Settings: test labs shown)
NEAREST = [m("pf_lp_best = 999"), setg("pf_lp_uid", "none"),
           {"u_location_variable": g("pf_lp_av")},
           {"u_run_npc_eocs": [{"id": "PF_LP_near_one",
                                "condition": {"and": [m("value_or(u_pf_is_leader, 0) == 1"), m("value_or(u_pf_band, 0) > 0"), m("value_or(u_pf_resident, 0) == 0")]},
                                "effect": [{"u_location_variable": {"u_val": "pf_pos"}},
                                           {"if": m("distance(u_pf_pos, pf_lp_av) < pf_lp_best"), "then": [
                                               m("pf_lp_best = distance(u_pf_pos, pf_lp_av)"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_lp_uid")},
                                               setg("pf_lp_name", "<u_name>", True)]}]}],
            "local": True, "npc_range": 60}]
report = [say("[places lab] travelling: <global_val:pf_lp_tv> (band <global_val:pf_lp_tvb>, <global_val:pf_tv_name>), home set: <global_val:pf_lp_hs>, residents: <global_val:pf_lp_rn>, chief: <global_val:pf_lp_cs> <global_val:pf_chief_name>")]
for k in range(MAXP):
    report.append({"if": m(f"value_or(pf_pl_{k}_alive, 0) == 1"), "then": [
        m(f"pf_lp_n = pf_pl_{k}_n"), m(f"pf_lp_kn = value_or(pf_pl_{k}_known, 0)"), {"u_location_variable": g("pf_lp_av")},
        m(f"pf_lp_d = round(distance(pf_lp_av, pf_pl_{k}_at))"),
        say(f"[places lab] place {k}: <global_val:pf_pl_{k}_name>, founded by <global_val:pf_pl_{k}_fname>, <global_val:pf_lp_n> households, known <global_val:pf_lp_kn>, <global_val:pf_lp_d> tiles away")]})
files["lab_places.json"] = [
    eoc("PF_PLACE_lab_shown", [{"run_eocs": "PF_PLACE_lab"}], "The Places lab, only with Settings: test labs shown.", condition=m("value_or(pf_set_labs, 0) == 1")),
    eoc("PF_PLACE_lab", [{"run_eoc_selector": ["PF_LP_know", "PF_LP_settle", "PF_LP_drift", "PF_LP_census", "PF_LP_report", "PF_LP_nohouse"],
        "names": ["Nearest band knows you well (saved life x2 with each)", "Settle the nearest band where it stands (it founds or joins a place)",
                  "Run the daily world drift now", "Run the daily place census now", "Report places and travel", "[test] Forget your home and household count"],
        "keys": ["a", "b", "c", "d", "e", "f"], "title": "[lab] Places and travel (v0.9)", "allow_cancel": True}]),
    eoc("PF_LP_know", [
        {"u_run_npc_eocs": [{"id": "PF_LP_know_one",
                             "condition": {"and": [m("value_or(u_pf_band, 0) > 0"), m("value_or(u_pf_resident, 0) == 0"), {"not": {"u_has_trait": "PF_CHILD"}}]},
                             "effect": [m("pf_m_str_in = 90"), {"run_eocs": "PF_MK_saved_life", "alpha_talker": "avatar", "beta_talker": "u"},
                                        {"run_eocs": "PF_MK_saved_life", "alpha_talker": "avatar", "beta_talker": "u"}]}],
         "local": True, "npc_range": 60},
        say("[places lab] Everyone in a band within 60 tiles: you saved their life, twice."),
    ]),
    eoc("PF_LP_settle", NEAREST + [
        {"if": {"compare_string": [g("pf_lp_uid"), "none"]}, "then": [say("[places lab] No band leader within 60 tiles.")],
         "else": [by_uid([{"id": "PF_LP_settle_one", "effect": [
                      {"u_location_variable": {"u_val": "pf_vpos"}}, m("u_pf_settled = 1"), m("u_pf_camp_until = 0"),
                      {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_home"}},
                      {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_wp_b"}},
                      {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_goal"}},
                      m("pf_pl_join_only = 0"), {"run_eocs": "PF_PLACE_found_or_join"},
                      setg("pf_lp_pn", "(none)"), {"if": m("value_or(u_pf_place, 0) > 0"), "then": [{"copy_var": {"u_val": "pf_place_name"}, "target_var": g("pf_lp_pn")}]}]}],
                     g("pf_lp_uid")),
                  say("[places lab] <global_val:pf_lp_name>'s band settled; place: <global_val:pf_lp_pn>, joined an existing one: <global_val:pf_pl_joined>.")]},
    ]),
    eoc("PF_LP_drift", [{"run_eocs": "PF_WORLD_drift_tick"}, say("[places lab] Ran the daily drift.  Places founded <global_val:pf_places_founded_total>, joined <global_val:pf_places_joined_total>, camps <global_val:pf_world_camps_total>.")]),
    eoc("PF_LP_census", [{"run_eocs": "PF_PLACE_tick"}, say("[places lab] Ran the census.")]),
    eoc("PF_LP_report", [m("pf_lp_tv = value_or(pf_tv_on, 0)"), m("pf_lp_tvb = value_or(pf_tv_band, 0)"), m("pf_lp_hs = value_or(pf_home_set, 0)"),
                         m("pf_lp_rn = value_or(pf_residents_n, 0)"), m("pf_lp_cs = value_or(pf_chief_set, 0)")] + report),
    eoc("PF_LP_nohouse", [m("pf_home_set = 0"), m("pf_residents_n = 0"), say("[places lab] Home forgotten and the household count set to 0 (the people stay; only for testing Ask to live with them).")]),
]

os.makedirs(OUT, exist_ok=True)
for name, objs in files.items():
    json.dump(objs, open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n"), indent=2)
print("places written:", {k: len(v) for k, v in files.items()})
