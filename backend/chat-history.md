# Chat history

When a student reopens chat, they should see their previous messages
and Trinket’s replies in the order they were sent.

For each message, save:
- The signed-in student’s user ID
- Who sent it: the student or Trinket
- The message text
- When it was sent

Students should only be able to load their own messages.

## First version

- When the student opens chat, load their 20 most recent messages and display them oldest first.
- When a chat request succeeds, save the student's message and Trinket's reply together under the signed-in student's account.
- If loading or saving fails, show an error so the student knows what happened.

## How to check it

Send a message, close and reopen the app, and check that both the message
and reply are still there. Sign in as a different test user and check that
the first student’s conversation is hidden.

## API plan

- Keep `POST /chat` for sending a message. Once a reply is generated,
  save the student's message and Trinket's reply together.
- Add `GET /chat/history` to return the signed-in student's latest
  20 messages, oldest first.
- Use the signed-in session to identify the student. Return HTTP 401
  if the request has no valid session.