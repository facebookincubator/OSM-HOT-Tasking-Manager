from backend import db
from backend.models.dtos.team_dto import (
    TeamDTO,
    NewTeamDTO,
    TeamMembersDTO,
    TeamProjectDTO,
    TeamMembersStatsDTO,
    TeamMembersStatsQuery,
    TeamMemberStats,
)
from backend.models.dtos.organisation_dto import OrganisationTeamsDTO
from backend.models.postgis.organisation import Organisation
from backend.models.postgis.statuses import (
    TeamVisibility,
    TeamMemberFunctions,
    TeamRoles,
)
from backend.models.postgis.user import User
from backend.models.postgis.task import TaskHistory
from backend.models.postgis.utils import NotFound

from sqlalchemy.sql.expression import cast, or_
from sqlalchemy import func, Time


class TeamMembers(db.Model):
    __tablename__ = "team_members"
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", name="fk_teams"), primary_key=True
    )
    user_id = db.Column(
        db.BigInteger, db.ForeignKey("users.id", name="fk_users"), primary_key=True
    )
    function = db.Column(db.Integer, nullable=False)  # either 'editor' or 'manager'
    active = db.Column(db.Boolean, default=False)
    join_request_notifications = db.Column(
        db.Boolean, nullable=False, default=False
    )  # Managers can turn notifications on/off for team join requests
    member = db.relationship(
        User, backref=db.backref("teams", cascade="all, delete-orphan")
    )
    team = db.relationship(
        "Team", backref=db.backref("members", cascade="all, delete-orphan")
    )

    def create(self):
        """ Creates and saves the current model to the DB """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """ Deletes the current model from the DB """
        db.session.delete(self)
        db.session.commit()

    def update(self):
        """ Updates the current model in the DB """
        db.session.commit()

    @staticmethod
    def get(team_id: int, user_id: int):
        """ Returns a team member by team_id and user_id """
        return TeamMembers.query.filter_by(team_id=team_id, user_id=user_id).first()


class Team(db.Model):
    """ Describes a team """

    __tablename__ = "teams"

    # Columns
    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer,
        db.ForeignKey("organisations.id", name="fk_organisations"),
        nullable=False,
    )
    name = db.Column(db.String(512), nullable=False)
    logo = db.Column(db.String)  # URL of a logo
    description = db.Column(db.String)
    invite_only = db.Column(db.Boolean, default=False, nullable=False)
    visibility = db.Column(
        db.Integer, default=TeamVisibility.PUBLIC.value, nullable=False
    )

    organisation = db.relationship(Organisation, backref="teams")

    def create(self):
        """ Creates and saves the current model to the DB """
        db.session.add(self)
        db.session.commit()

    @classmethod
    def create_from_dto(cls, new_team_dto: NewTeamDTO):
        """ Creates a new team from a dto """
        new_team = cls()

        new_team.name = new_team_dto.name
        new_team.description = new_team_dto.description
        new_team.invite_only = new_team_dto.invite_only
        new_team.visibility = TeamVisibility[new_team_dto.visibility].value

        org = Organisation.get(new_team_dto.organisation_id)
        new_team.organisation = org

        # Create team member with creator as a manager
        new_member = TeamMembers()
        new_member.team = new_team
        new_member.user_id = new_team_dto.creator
        new_member.function = TeamMemberFunctions.MANAGER.value
        new_member.active = True

        new_team.members.append(new_member)

        new_team.create()
        return new_team

    def update(self, team_dto: TeamDTO):
        """ Updates Team from DTO """
        if team_dto.organisation:
            self.organisation = Organisation().get_organisation_by_name(
                team_dto.organisation
            )

        for attr, value in team_dto.items():
            if attr == "visibility" and value is not None:
                value = TeamVisibility[team_dto.visibility].value

            if attr in ("members", "organisation"):
                continue

            try:
                is_field_nullable = self.__table__.columns[attr].nullable
                if is_field_nullable and value is not None:
                    setattr(self, attr, value)
                elif value is not None:
                    setattr(self, attr, value)
            except KeyError:
                continue

        if team_dto.members != self._get_team_members() and team_dto.members:
            for member in self.members:
                member_name = User.get_by_id(member.user_id).username
                if member_name not in [i["username"] for i in team_dto.members]:
                    member.delete()
            for member in team_dto.members:
                user = User.get_by_username(member["username"])
                if user is None:
                    raise NotFound("User not found")
                team_member = TeamMembers.get(self.id, user.id)
                if team_member:
                    team_member.join_request_notifications = member[
                        "join_request_notifications"
                    ]
                else:
                    new_team_member = TeamMembers()
                    new_team_member.team = self
                    new_team_member.member = user
                    new_team_member.function = TeamMemberFunctions[
                        member["function"]
                    ].value

        db.session.commit()

    def delete(self):
        """ Deletes the current model from the DB """
        db.session.delete(self)
        db.session.commit()

    def can_be_deleted(self) -> bool:
        """ A Team can be deleted if it doesn't have any projects """
        return len(self.projects) == 0

    def get(team_id: int):
        """
        Gets specified team by id
        :param team_id: team ID in scope
        :return: Team if found otherwise None
        """
        return Team.query.get(team_id)

    def get_team_by_name(team_name: str):
        """
        Gets specified team by name
        :param team_name: team name in scope
        :return: Team if found otherwise None
        """
        return Team.query.filter_by(name=team_name).one_or_none()

    def as_dto(self):
        """ Returns a dto for the team """
        team_dto = TeamDTO()
        team_dto.team_id = self.id
        team_dto.description = self.description
        team_dto.invite_only = self.invite_only
        team_dto.members = self._get_team_members()
        team_dto.name = self.name
        team_dto.organisation = self.organisation.name
        team_dto.organisation_id = self.organisation.id
        team_dto.logo = self.organisation.logo
        team_dto.visibility = TeamVisibility(self.visibility).name
        return team_dto

    def as_dto_inside_org(self):
        """ Returns a dto for the team """
        team_dto = OrganisationTeamsDTO()
        team_dto.team_id = self.id
        team_dto.name = self.name
        team_dto.description = self.description
        team_dto.invite_only = self.invite_only
        team_dto.members = self._get_team_members()
        team_dto.visibility = TeamVisibility(self.visibility).name
        return team_dto

    def as_dto_team_member(self, member) -> TeamMembersDTO:
        """ Returns a dto for the team  member"""
        member_dto = TeamMembersDTO()
        user = User.get_by_id(member.user_id)
        member_function = TeamMemberFunctions(member.function).name
        member_dto.username = user.username
        member_dto.function = member_function
        member_dto.picture_url = user.picture_url
        member_dto.active = member.active
        member_dto.join_request_notifications = member.join_request_notifications
        return member_dto

    def as_dto_team_project(self, project) -> TeamProjectDTO:
        """ Returns a dto for the team project """
        project_team_dto = TeamProjectDTO()
        project_team_dto.project_name = project.name
        project_team_dto.project_id = project.project_id
        project_team_dto.role = TeamRoles(project.role).name
        return project_team_dto

    def _get_team_members(self):
        """ Helper to get JSON serialized members """
        members = []
        for mem in self.members:
            members.append(
                {
                    "username": mem.member.username,
                    "pictureUrl": mem.member.picture_url,
                    "function": TeamMemberFunctions(mem.function).name,
                    "active": mem.active,
                }
            )

        return members

    def get_team_managers(self):
        return TeamMembers.query.filter_by(
            team_id=self.id, function=TeamMemberFunctions.MANAGER.value, active=True
        ).all()

    @staticmethod
    def get_team_members_stats(query: TeamMembersStatsQuery) -> TeamMembersStatsDTO:
        """Get team stats by member """
        team = Team.get(query.team_id)
        members = team.members
        projects = team.projects
        project_ids = [project.project_id for project in projects]

        team_stats = TeamMembersStatsDTO()
        for member in members:
            user = User.get_by_id(member.user_id)
            member_stats = TeamMemberStats()
            member_stats.user_id = user.id
            member_stats.username = user.username
            member_stats.picture_url = user.picture_url

            member_stats.total_time_spent = 0
            member_stats.tasks_mapped = 0
            member_stats.tasks_validated = 0
            member_stats.time_spent_mapping = 0
            member_stats.time_spent_validating = 0
            member_stats.average_mapping_time = 0
            member_stats.average_validation_time = 0

            map_stats = (
                db.session.query(
                    func.sum(
                        cast(
                            func.to_timestamp(TaskHistory.action_text, "HH24:MI:SS"),
                            Time,
                        )
                    ),
                    func.count(TaskHistory.task_id),
                    func.avg(
                        cast(
                            func.to_timestamp(TaskHistory.action_text, "HH24:MI:SS"),
                            Time,
                        )
                    ),
                )
                .filter(
                    or_(
                        TaskHistory.action == "LOCKED_FOR_MAPPING",
                        TaskHistory.action == "AUTO_UNLOCKED_FOR_MAPPING",
                    )
                )
                .filter(TaskHistory.user_id == user.id)
                .filter(TaskHistory.project_id.in_(project_ids))
                .filter(
                    TaskHistory.action_date.between(query.start_date, query.end_date)
                )
            )

            for time, tasks_mapped, avg_mapping_time in map_stats:
                if time:
                    member_stats.time_spent_mapping = time.total_seconds()
                    member_stats.total_time_spent += member_stats.time_spent_mapping
                member_stats.tasks_mapped = tasks_mapped
                member_stats.average_mapping_time = (
                    avg_mapping_time.total_seconds()
                    if avg_mapping_time is not None
                    else 0
                )

            validation_stats = (
                db.session.query(
                    func.sum(
                        cast(
                            func.to_timestamp(TaskHistory.action_text, "HH24:MI:SS"),
                            Time,
                        )
                    ),
                    func.count(TaskHistory.task_id),
                    func.avg(
                        cast(
                            func.to_timestamp(TaskHistory.action_text, "HH24:MI:SS"),
                            Time,
                        )
                    ),
                )
                .filter(
                    or_(
                        TaskHistory.action == "LOCKED_FOR_VALIDATION",
                        TaskHistory.action == "AUTO_UNLOCKED_FOR_VALIDATION",
                    )
                )
                .filter(TaskHistory.user_id == user.id)
                .filter(TaskHistory.project_id.in_(project_ids))
                .filter(
                    TaskHistory.action_date.between(query.start_date, query.end_date)
                )
            )

            for time, tasks_validated, avg_validation_time in validation_stats:
                if time:
                    member_stats.time_spent_validating = time.total_seconds()
                    member_stats.total_time_spent += member_stats.time_spent_validating
                member_stats.tasks_validated = tasks_validated
                member_stats.average_validation_time = (
                    avg_validation_time.total_seconds()
                    if avg_validation_time is not None
                    else 0
                )

            team_stats.members_stats.append(member_stats)
        return team_stats
