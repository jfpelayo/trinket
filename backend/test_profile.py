#testing on retrieving data from Supabase

from getpass import getpass

from profiles import connect, get_profile, save_profile


def main():
    client = connect()

    email = input("Test account email: ").strip()
    password = getpass("Test account password: ")

    client.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })

    try:
        print("Before:", get_profile(client))
        save_profile(
    client,
    "Hiro",
    timezone="America/Los_Angeles",
    preferred_study_time="14:30",
    communication_style="concise",
    focus_session_minutes=25,
)
        print("After:", get_profile(client))
    finally:
        client.auth.sign_out()


if __name__ == "__main__":
    main()