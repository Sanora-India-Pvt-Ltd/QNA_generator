import { OAuth2Client } from "google-auth-library";

const client = new OAuth2Client(
  "804599806902-fdh2279lqo96btm255232u83ae6je06p.apps.googleusercontent.com",
  "YOUR_CLIENT_SECRET",
  "http://localhost:5000/api/auth/google/callback"
);

export const googleLogin = (req, res) => {
  const url = client.generateAuthUrl({
    access_type: "offline",
    scope: ["profile", "email"],
  });

  res.redirect(url);
};

export const googleCallback = async (req, res) => {
  const code = req.query.code;

  const { tokens } = await client.getToken(code);
  client.setCredentials(tokens);

  const ticket = await client.verifyIdToken({
    idToken: tokens.id_token,
    audience: "804599806902-fdh2279lqo96btm255232u83ae6je06p.apps.googleusercontent.com",
  });

  const payload = ticket.getPayload();

  res.redirect(
    `http://localhost:5173/profile?` +
      `name=${payload.name}&` +
      `email=${payload.email}&` +
      `picture=${payload.picture}`
  );
};
