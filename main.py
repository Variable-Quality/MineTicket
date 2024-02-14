import discord
import configparser
import mariadb

from dataclasses import dataclass
import datetime

cfg = configparser.ConfigParser()
cfg.read("token.ini")
TOKEN = cfg["SECRET"]["token"]


class Client(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}!")

    async def on_message(self, message):
        print(f"Message recieved from {message.author}: {message.content}")


@dataclass
class TicketInfo:
    start_time: int = 0
    thirtySecTime: int = start_time + 30


# Get field info from cursor
def get_field_info(dbConnection):
    """Retrieves the field info associated with a cursor"""

    field_info = mariadb.fieldinfo()

    field_info_text = []

    # Retrieve Column Information
    for column in cur.description:
        column_name = column[0]
        column_type = field_info.type(column)
        column_flags = field_info.flag(column)

        field_info_text.append(f"{column_name}: {column_type} {column_flags}")

    return field_info_text


# Get field info from cursor
def get_table_field_info(dbConnection, table):
    """Retrieves the field info associated with a table"""

    # Fetch Table Information
    cur.execute(f"SELECT * FROM {table} LIMIT 1")

    field_info_text = get_field_info(cur)

    return field_info_text


@tasks.loop(seconds=30)
async def pullFromDB(ctx, dbConnection):
    """
    pull from DB every 30 seconds
    When we do the pull, take down current time and substract 30seconds
    check for tickets between those two times
    print ticket info to discord sequentially
    """
    TicketInfo.start_time = ctx.message.created_at
    # Get list of tables

    # Retrieve Contacts
    dbConnection.execute("SHOW TABLES")
    tempList = []

    for (table,) in dbConnection.fetchall():
        tempList.append(table)

    await channel.send(f"Last entry: {x for x in tempList}")

    return


try:
    conn = mariadb.connect(
        host="192.0.2.1",
        port=3306,
        user="db_user",
        password="USER_PASSWORD",
        database="test",
    )

    dbConnection = conn.cursor()

    tables = show_tables(dbConnection)

    for table in tables:
        field_info_text = get_table_field_info(dbConnection, table)

        print(f"Columns in table {table}:")
        print("\n".join(field_info_text))
        print("\n")

    conn.close()

except Exception as e:
    print(f"Error: {e}")


intents = discord.Intents.default()
intents.message_content = True

client = Client(intents=intents)
client.run(TOKEN)
