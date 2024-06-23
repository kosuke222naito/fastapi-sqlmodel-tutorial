from fastapi import FastAPI, HTTPException, Query, Depends
from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship


class TeamBase(SQLModel):
    name: str = Field(index=True)
    headquarters: str


class Team(TeamBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    heroes: list["Hero"] = Relationship(back_populates="team")


class TeamCreate(TeamBase):
    pass


class TeamPublic(TeamBase):
    id: int


class TeamUpdate(SQLModel):
    name: str | None = None
    headquarters: str | None = None


class HeroBase(SQLModel):
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)

    team_id: int | None = Field(default=None, foreign_key="team.id")


class Hero(HeroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str = Field()

    team: "Team" = Relationship(back_populates="heroes")


class HeroCreate(HeroBase):
    password: str


class HeroPublic(HeroBase):
    id: int


class HeroUpdate(SQLModel):
    name: str | None = None
    secret_name: str | None = None
    age: int | None = None
    password: str | None = None
    team_id: int | None = None


class HeroPublicWithTeam(HeroPublic):
    team: TeamPublic | None = None


class TeamPublicWithHeroes(TeamPublic):
    heroes: list[HeroPublic] = []


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def init_data():
    heroes = [
        HeroCreate(
            name="Deadpond", secret_name="Dive Wilson", password="hased password"
        ),
        HeroCreate(
            name="Spider-Boy",
            secret_name="Pedro Parqueador",
            password="hased password",
        ),
        HeroCreate(
            name="Rusty-Man",
            secret_name="Tommy Sharp",
            age=48,
            password="hased password",
        ),
        HeroCreate(
            name="Tarantula",
            secret_name="Natalia Roman-on",
            age=32,
            password="hased password",
        ),
        HeroCreate(
            name="Black Lion",
            secret_name="Trevor Challa",
            age=35,
            password="hased password",
        ),
        HeroCreate(
            name="Dr. Weird",
            secret_name="Steve Weird",
            age=36,
            password="hased password",
        ),
        HeroCreate(
            name="Captain North America",
            secret_name="Esteban Rogelios",
            age=93,
            password="hased password",
        ),
    ]

    for hero in heroes:
        with Session(engine) as session:
            hashed_password = hash_password(hero.password)
            extra_data = {"hashed_password": hashed_password}
            db_hero = Hero.model_validate(hero, update=extra_data)
            session.add(db_hero)
            session.commit()
            session.refresh(db_hero)


def hash_password(password: str) -> str:
    # Use something like passlib here
    return f"not really hashed {password} hehehe"


app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # init_data()


@app.post("/teams/", response_model=TeamPublic)
def create_team(*, session: Session = Depends(get_session), team: TeamCreate):
    db_team = Team.model_validate(team)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    return db_team


@app.get("/teams/", response_model=list[TeamPublic])
def read_teams(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
):
    teams = session.exec(select(Team).offset(offset).limit(limit)).all()
    return teams


@app.get("/teams/{team_id}", response_model=TeamPublic)
def read_team(*, session: Session = Depends(get_session), team_id: int):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@app.patch("/teams/{team_id}", response_model=TeamPublic)
def update_team(
    *,
    session: Session = Depends(get_session),
    team_id: int,
    team: TeamUpdate,
):
    db_team = session.get(Hero, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    team_data = team.model_dump(exclude_unset=True)
    for key, value in team_data.items():
        setattr(db_team, key, value)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    return db_team


@app.delete("/teams/{team_id}")
def delete_team(*, session: Session = Depends(get_session), team_id: int):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team)
    session.commit()
    return {"ok": True}


@app.post("/heroes/", response_model=HeroPublic)
def create_hero(*, session: Session = Depends(get_session), hero: HeroCreate):
    hashed_password = hash_password(hero.password)
    extra_data = {"hashed_password": hashed_password}
    db_hero = Hero.model_validate(hero, update=extra_data)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero


@app.get("/heroes/", response_model=list[HeroPublic])
def read_heroes(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
):
    heroes = session.exec(select(Hero).offset(offset).limit(limit)).all()
    return heroes


@app.get("/heroes/{hero_id}", response_model=HeroPublic)
def read_hero(*, session: Session = Depends(get_session), hero_id: int):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero


@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(
    *, session: Session = Depends(get_session), hero_id: int, hero: HeroUpdate
):
    db_hero = session.get(Hero, hero_id)
    if not db_hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    hero_data = hero.model_dump(exclude_unset=True)
    extra_data: dict[str, str | int] = {}
    if "password" in hero_data:
        password = hero_data["password"]
        hashed_password = hash_password(password)
        extra_data["hashed_password"] = hashed_password
    db_hero.sqlmodel_update(hero_data, update=extra_data)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero


@app.delete("/heroes/{hero_id}")
def delete_hero(*, session: Session = Depends(get_session), hero_id: int):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(hero)
    session.commit()
    return {"ok": True}
