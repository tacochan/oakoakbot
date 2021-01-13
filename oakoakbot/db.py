import csv
import datetime
import glob
import os
import random

from peewee import (
    SqliteDatabase,
    Model,
    IntegerField,
    CharField,
    FloatField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
)

from oakoakbot.logger import get_logger

SHINY_CHANCE = 0.001

POKEMON_CSV = "data/pokemon.csv"
DB_FILE = "data/oak_db.sqlite3"
SPRITES_FOLDER = "data/images/pokemon"


logger = get_logger()

db = SqliteDatabase(DB_FILE)


class CustomModel(Model):
    class Meta:
        database = db


class Pokemon(CustomModel):
    number = IntegerField()
    name = CharField()
    form = IntegerField(default=1)
    region = CharField(default="global")
    type_1 = CharField()
    type_2 = CharField()
    ability_1 = CharField()
    ability_2 = CharField()
    ability_hidden = CharField()
    generation = IntegerField()
    legendary = BooleanField()
    mega = BooleanField()
    height = FloatField()
    weight = FloatField()
    hp = IntegerField()
    attack = IntegerField()
    defense = IntegerField()
    special_attack = IntegerField()
    special_defense = IntegerField()
    speed = IntegerField()
    total = IntegerField()


class PokemonNatures(CustomModel):
    name = CharField()
    increases = CharField()
    decreases = CharField()


class GroupsConfiguration(CustomModel):
    pokemon_rate = FloatField()
    generations = CharField()


class Teams(CustomModel):
    user_id = CharField()
    group_id = CharField()


class CaughtPokemon(CustomModel):
    team_id = ForeignKeyField(Teams)
    pokemon_id = ForeignKeyField(Pokemon)
    catch_date = DateTimeField(default=datetime.datetime.now)
    level = IntegerField(default=1)
    shiny = BooleanField()
    gender = CharField()
    ability = CharField()
    nature = CharField()
    hp_iv = IntegerField()
    attack_iv = IntegerField()
    defense_iv = IntegerField()
    special_attack_iv = IntegerField()
    special_defense_iv = IntegerField()
    speed_iv = IntegerField()


class WildPokemon:
    def __init__(self, number, include_alolan, include_galarian):
        self.shiny = False
        if random.random() < SHINY_CHANCE:
            self.shiny = True

        shiny_flag = "r" if self.shiny else "n"
        filename = f"poke_capture_{number:04}*_{shiny_flag}.png"

        sprites = glob.glob(os.path.join(SPRITES_FOLDER, filename))

        # Exclude mega evolution sprites
        sprites = [sprite for sprite in sprites if "_m_" in sprite]

        # Exclude alolan and galarian forms if specified
        if include_alolan is False:
            sprites = [sprite for sprite in sprites if "_a_" in sprite]
        if include_galarian is False:
            sprites = [sprite for sprite in sprites if "_g_" in sprite]

        self.sprite_filename = sprites[random.randint(0, len(sprites) - 1)]

        attributes = self.sprite_filename.split("_")
        self.form = attributes[3]
        self.gender = attributes[4]
        self.region = attributes[5]


class OakDB:
    def __init__(self):
        db.connect()
        db.create_tables(
            [Pokemon, PokemonNatures, Teams, GroupsConfiguration, CaughtPokemon]
        )

        if Pokemon.select().count() == 0:
            logger.info("Pokemon table is empty")
            self.init_pokemon_table()

        self.group_configuration = GroupsConfiguration.select()

    def init_pokemon_table(self):
        with open(POKEMON_CSV, "r") as csv_file:
            rows = csv.DictReader(csv_file)
            pokemon_to_add = []
            for r in rows:
                pokemon_to_add.append(
                    Pokemon(
                        number=r["NUMBER"],
                        name=r["NAME"],
                        type_1=r["TYPE1"],
                        type_2=r["TYPE2"],
                        ability_1=r["ABILITY1"],
                        ability_2=r["ABILITY2"],
                        ability_hidden=r["ABILITY HIDDEN"],
                        generation=r["GENERATION"],
                        legendary=int(r["LEGENDARY"]),
                        mega=int(r["MEGA_EVOLUTION"]),
                        height=r["HEIGHT"],
                        weight=r["WEIGHT"],
                        hp=r["HP"],
                        attack=r["ATK"],
                        defense=r["DEF"],
                        special_attack=r["SP_ATK"],
                        special_defense=r["SP_DEF"],
                        speed=r["SPD"],
                        total=r["TOTAL"],
                    )
                )
            Pokemon.bulk_create(pokemon_to_add)

        pass

    def update_group_pokemon_rate(self, group_id: int, rate: float):
        # GroupConfiguration TODO: Insert into DB
        # self.group_configuration[group_id]["rate"] = rate
        pass

    def update_group_generations(self, group_id: int, generations: list):
        # GroupConfiguration TODO: Insert into DB
        # self.group_configuration[group_id]["generations"] = generations
        pass

    def get_group_pokemon_rate(self, group_id: int) -> float:
        return self.group_configuration[group_id]["rate"]

    def get_pokemon(self, group_id: int) -> WildPokemon:
        return WildPokemon(self)

    def capture_pokemon(self, user_id: int, group_id: int, pokemon: Pokemon):
        pass
