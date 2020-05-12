from lunch_buddies.lib.service_context import service_context


def migrate():
    team_settings = service_context.daos.team_settings.read(None, None)
    teams = service_context.daos.teams.read(None, None)

    for team in teams:
        team_s = [t for t in team_settings if t.team_id == team.team_id]
        feature_notify_in_channel = team_s[0].feature_notify_in_channel if len(team_s) else False

        print('For {} setting feature_notify_in_channel={}'.format(team.team_id, feature_notify_in_channel))

        service_context.daos.teams.update(team, team._replace(feature_notify_in_channel=feature_notify_in_channel))
