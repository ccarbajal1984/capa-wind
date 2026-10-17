export default {
  async scheduled(_event, env, _ctx) {
    const response = await fetch(
      "https://api.github.com/repos/ccarbajal1984/capa-wind/actions/workflows/update.yml/dispatches",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GH_TOKEN}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "capa-wind-ticker",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ref: "main" }),
      }
    );
    if (response.status !== 204) {
      const body = await response.text();
      console.log(`GitHub dispatch returned ${response.status}: ${body.slice(0, 500)}`);
    }
  },

  fetch() {
    return new Response("Not found\n", { status: 404, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  },
};
