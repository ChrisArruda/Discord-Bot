# 🏈 NFL Game Notifications

Get notified when your favorite NFL team is playing with automatic game updates and score alerts!

## 📋 Available Commands

### Set Your Favorite Team
```
!set_team NFL <team_name>
```
Example: `!set_team NFL 49ers`

### Configure Notifications
```
!notify_settings [enabled=true/false] [timezone=Your/Timezone] [notify_before=60] 
                [notify_start=true/false] [notify_scores=true/false] [notify_final=true/false]
```
- `enabled`: Enable/disable all notifications (default: true)
- `timezone`: Your timezone (e.g., America/New_York)
- `notify_before`: Minutes before game to notify (default: 60)
- `notify_start`: Get notified when game starts (default: true)
- `notify_scores`: Get score updates (default: true)
- `notify_final`: Get final score (default: true)

### Check Team Schedule
```
!team_schedule <team_name>
```
Example: `!team_schedule Chiefs`

### View Your Teams
```
!my_teams [@user]
```
Shows your or another user's favorite teams.

## 🔔 Notification Types

1. **Game Reminders**
   - 24 hours before game
   - 6 hours before game
   - 1 hour before game
   - 30 minutes before game
   - 15 minutes before game
   - 5 minutes before game

2. **Game Start**
   - When the game begins

3. **Quarter/Period Updates**
   - End of each quarter
   - Overtime updates

4. **Final Score**
   - Game results and final score

## ⚙️ Default Settings
- Notifications: Enabled
- Timezone: UTC
- Reminder: 60 minutes before game
- All notification types: Enabled

## 📝 Notes
- Make sure your DMs are open to receive notifications
- Use the `!notify_settings` command without any arguments to see your current settings
- To see a list of all valid team names, use `!teams NFL`

## 🕒 Timezones
Specify your timezone using the [TZ database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).
Examples:
- `America/New_York`
- `America/Chicago`
- `America/Los_Angeles`
- `Europe/London`

## ❓ Need Help?
Contact a server administrator or use the `!help` command for more information.
