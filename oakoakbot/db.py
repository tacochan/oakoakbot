import csv
import datetime
import glob
import os
import random
import time

from peewee import (
    fn,
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

DEFAULT_SPAWN_RATE = 1 / 133
NUM_GENERATIONS = 8

POKEMON_CSV = "data/pokemon.csv"
DB_FILE = "data/oak_db.sqlite3"
SPRITES_FOLDER = "data/images/pokemon"


logger = get_logger()

db = SqliteDatabase(DB_FILE)


class WildEncounter:
    def __init__(self, pokemon, shiny=False):
        self.pokemon = pokemon
        self.release_time = time.time()
        self.nature = PokemonNatures.get_random_nature()
        self.shiny = shiny

        # Pick an ability at random with less chance of having secondary/hidden ability
        self.ability = self.pokemon.ability_1
        if self.pokemon.ability_2 and random.random() < 0.3:
            self.ability = self.pokemon.ability_2
        if self.pokemon.ability_hidden and random.random() < 0.1:
            self.ability = self.pokemon.ability_hidden

        filename = f"{pokemon.number:04}_{pokemon.form:02}_{pokemon.region}"
        filename += "_s" if self.shiny else "_n"
        filename += "_m" if self.pokemon.mega else "_n"

        sprites = glob.glob(os.path.join(SPRITES_FOLDER, filename + "*.png"))

        self.sprite_filename = sprites[random.randint(0, len(sprites) - 1)]

        attributes = self.sprite_filename.split("_")
        self.gender = attributes[-1].replace(".png", "")


class CustomModel(Model):
    class Meta:
        database = db


class PokemonNatures(CustomModel):
    name = CharField()
    increases = CharField()
    decreases = CharField()

    @staticmethod
    def init_table_from_csv(csv_filename):
        PokemonNatures.delete().execute()
        with open(csv_filename, "r") as csv_file:
            rows = csv.DictReader(csv_file)
            PokemonNatures.insert_many(rows).execute()

    @staticmethod
    def get_random_nature():
        return PokemonNatures.select().order_by(fn.Random()).limit(1).execute()[0].id


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
    enabled = BooleanField()
    rarity_tier = CharField()

    @staticmethod
    def init_table_from_csv(csv_filename):
        Pokemon.delete().execute()
        with open(csv_filename, "r") as csv_file:
            pokemon = list(csv.DictReader(csv_file))
            for p in pokemon:
                p["legendary"] = bool(int(p["legendary"]))
                p["mega"] = bool(int(p["mega"]))
                p["enabled"] = bool(int(p["enabled"]))
            Pokemon.insert_many(pokemon).execute()

    @staticmethod
    def get_random_encounter(group_id, rarity_tier, shiny=False) -> WildEncounter:
        generations = GroupsConfiguration.get_generations(group_id)
        pokemon = (
            Pokemon.select()
            .where(
                (
                    Pokemon.number
                    == Pokemon.select(Pokemon.number)
                    .where(
                        Pokemon.generation.in_(generations)
                        & (Pokemon.mega == 0)
                        & (Pokemon.enabled == 1)
                        & (Pokemon.rarity_tier == rarity_tier)
                    )
                    .group_by(Pokemon.number)
                    .order_by(fn.Random())
                    .limit(1)
                )
                & (Pokemon.mega == 0)
                & (Pokemon.enabled == 1)
                & (Pokemon.rarity_tier == rarity_tier)
            )
            .order_by(fn.Random())
            .limit(1)
            .execute()
        )[0]

        return WildEncounter(pokemon, shiny)


class Teams(CustomModel):
    user_id = CharField()
    group_id = CharField()


class CaughtPokemon(CustomModel):
    team = ForeignKeyField(Teams)
    pokemon = ForeignKeyField(Pokemon)
    team_pokemon_id = IntegerField()
    catch_date = DateTimeField(default=datetime.datetime.now)
    level = IntegerField(default=1)
    shiny = BooleanField()
    gender = CharField()
    ability = CharField()
    nature = ForeignKeyField(PokemonNatures)
    hp_iv = IntegerField()
    attack_iv = IntegerField()
    defense_iv = IntegerField()
    special_attack_iv = IntegerField()
    special_defense_iv = IntegerField()
    speed_iv = IntegerField()

    @staticmethod
    async def catch_pokemon(wild_encounter, user_id, group_id):
        team_id = (
            Teams.select(Teams.id)
            .where((Teams.user_id == user_id) & (Teams.group_id == group_id))
            .execute()
        )
        if not len(team_id):
            logger.info(f"User {user_id} started a brand new team.")
            team_id = Teams.insert(user_id=user_id, group_id=group_id).execute()
        else:
            team_id = team_id[0].id

        CaughtPokemon.insert(
            team=team_id,
            team_pokemon_id=CaughtPokemon.select()
            .where(CaughtPokemon.team_id == team_id)
            .count(),
            pokemon=wild_encounter.pokemon.id,
            catch_date=datetime.datetime.now(),
            shiny=wild_encounter.shiny,
            gender=wild_encounter.gender,
            ability=wild_encounter.ability,
            nature=wild_encounter.nature,
            hp_iv=random.randint(0, 31),
            attack_iv=random.randint(0, 31),
            defense_iv=random.randint(0, 31),
            special_attack_iv=random.randint(0, 31),
            special_defense_iv=random.randint(0, 31),
            speed_iv=random.randint(0, 31),
        ).execute()

    @staticmethod
    async def get_caught_pokemon(user_id, group_id):
        return list(
            CaughtPokemon.select()
            .join(Pokemon, on=(CaughtPokemon.pokemon == Pokemon.id))
            .where(
                CaughtPokemon.team
                == Teams.select(Teams.id).where(
                    (Teams.user_id == user_id) & (Teams.group_id == group_id)
                )
            )
            .order_by(CaughtPokemon.team_pokemon_id)
            .execute()
        )


class GroupsConfiguration(CustomModel):
    group_id = IntegerField(unique=True)
    pokemon_rate = FloatField(default=DEFAULT_SPAWN_RATE)
    generations = CharField(
        default=",".join(str(gen) for gen in range(1, NUM_GENERATIONS + 1))
    )

    @staticmethod
    def add_group(group_id):
        GroupsConfiguration.insert(group_id=group_id).execute()

    @staticmethod
    def get_groups():
        groups = GroupsConfiguration.select(GroupsConfiguration.group_id).execute()
        return [group.group_id for group in groups]

    @staticmethod
    def set_pokemon_rate(group_id, pokemon_rate):
        updated_rows = (
            GroupsConfiguration.update(pokemon_rate=pokemon_rate)
            .where(GroupsConfiguration.group_id == group_id)
            .execute()
        )
        return updated_rows == 1

    @staticmethod
    def get_pokemon_rate(group_id):
        return (
            GroupsConfiguration.select(GroupsConfiguration.pokemon_rate)
            .where(GroupsConfiguration.group_id == group_id)
            .execute()
        )[0].pokemon_rate

    @staticmethod
    def set_generations(group_id, generations):
        generations_serialized = ",".join(str(gen) for gen in generations)
        updated_rows = (
            GroupsConfiguration.update(generations=generations_serialized)
            .where(GroupsConfiguration.group_id == group_id)
            .execute()
        )
        return updated_rows == 1

    @staticmethod
    def get_generations(group_id):
        generations = (
            GroupsConfiguration.select(GroupsConfiguration.generations)
            .where(GroupsConfiguration.group_id == group_id)
            .execute()
        )[0].generations
        return [int(gen) for gen in generations.split(",")]


db.connect()
db.create_tables([Pokemon, PokemonNatures, Teams, GroupsConfiguration, CaughtPokemon])
