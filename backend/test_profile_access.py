from getpass import getpass

from profiles import connect, current_user_id


def main():
    client = connect()

    user_a_id = input("User A's UID: ").strip()
    email = input("User B's email: ").strip()
    password = getpass("User B's password: ")

    client.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })

    try:
        if current_user_id(client) == user_a_id:
            raise ValueError("Use User B's credentials, not User A's.")

        result = (
            client.table("profiles")
            .select("id")
            .eq("id", user_a_id)
            .execute()
        )

        assert result.data == [], "FAIL: User B can read User A's profile."
        print("PASS: User B cannot read User A's profile.")

        # Assign the ID its existing value to avoid changing profile fields.
        result = (
            client.table("profiles")
            .update({"id": user_a_id})
            .eq("id", user_a_id)
            .execute()
        )

        assert result.data == [], "FAIL: User B can update User A's profile."
        print("PASS: User B cannot update User A's profile.")
    finally:
        client.auth.sign_out()


if __name__ == "__main__":
    main()