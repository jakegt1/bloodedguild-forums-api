import requests


class BlizzardClient():

    def __init__(self, realm, apikey, character_name):
        self.realm = realm
        self.apikey = apikey
        self.char = character_name
        self.progress = None
        self.store_guild_progress()

    def initialize_tier_obj(self, boss_count):
        return {
            "progress": 0,
            "total": boss_count,
            "bosses": []
        }

    def add_boss(self, raid_tier, boss, tier_type):
        boss_obj = {
            "name": boss["name"]
        }
        if(tier_type == "normal"):
            killed = boss["normalKills"] > 0
        elif(tier_type == "heroic"):
            killed = boss["heroicKills"] > 0
        else:
            killed = boss["mythicKills"] > 0
        boss_obj["killed"] = killed
        raid_tier["bosses"].append(boss_obj)
        if(killed):
            raid_tier["progress"] += 1
        return raid_tier

    def produce_raid_obj(self, raid):
        total_bosses = len(raid["bosses"])
        normal = self.initialize_tier_obj(total_bosses)
        heroic = self.initialize_tier_obj(total_bosses)
        mythic = self.initialize_tier_obj(total_bosses)
        for boss in raid["bosses"]:
            normal = self.add_boss(normal, boss, "normal")
            heroic = self.add_boss(heroic, boss, "heroic")
            mythic = self.add_boss(mythic, boss, "mythic")
        return {
            "normal": normal,
            "heroic": heroic,
            "mythic": mythic
        }

    def produce_progression_info(self, json):
        raids = json["progression"]["raids"]
        progression = {}
        for raid in raids:
            if(raid["bosses"][0].get("mythicKills") is not None):
                progression[raid["name"]] = self.produce_raid_obj(raid)
        return progression

    def store_guild_progress(self):
        uri = "https://eu.api.battle.net/wow/character/"
        uri += self.realm + "/" + self.char
        req_params = {
            "locale": "en_GB",
            "fields": "progression",
            "apikey": self.apikey
        }
        req = requests.get(uri, req_params)
        response = None
        if(req.status_code == requests.codes.ok):
            response = self.produce_progression_info(req.json())
        else:
            response = {"error": "Failed to work. Bad api key?"}
        self.progress = response
        return response
