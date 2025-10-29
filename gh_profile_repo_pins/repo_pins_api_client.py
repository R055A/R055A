from gh_profile_repo_pins.repo_pins_exceptions import GitHubGraphQlClientError
import gh_profile_repo_pins.repo_pins_enum as enums
from requests import post, Response
from dataclasses import dataclass
from http import HTTPStatus


@dataclass
class GitHubCredentialData:
    username: str
    user_name: str
    user_id: int
    account_creation: str


class GitHubGraphQlClient:

    __GRAPH_QL_URL: str = "https://api.github.com/graphql"
    __GRAPH_QL_REPO_QUERY_NODE_DATA: str = """
      name
      stargazerCount
      forkCount
      owner { login }
      description
      url
      primaryLanguage { name color }
      isFork
      parent { nameWithOwner }
      isTemplate
      isArchived
      pushedAt
      createdAt
      updatedAt
    """
    __GRAPH_QL_REPO_PIN_QUERY_STR: str = f"""
    query ($login: String!, $num: Int!) {{
      user(login: $login) {{
        pinnedItems(
          first: $num
          types: [REPOSITORY]
        ) {{
          edges {{
            node {{
              ... on Repository {{
                {__GRAPH_QL_REPO_QUERY_NODE_DATA}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    __GRAPH_QL_REPO_QUERY_PAGINATION: str = """
      pageInfo { hasNextPage endCursor }
    """
    __GRAPH_QL_REPO_OWN_QUERY_STR: str = f"""
    query ($login: String!, $num: Int!, $after: String, $field: RepositoryOrderField!) {{
      user(login: $login) {{
        repositories(
          first: $num
          after: $after
          orderBy: {{ field: $field, direction: DESC }}
        ) {{
          {__GRAPH_QL_REPO_QUERY_PAGINATION}
          nodes {{
            {__GRAPH_QL_REPO_QUERY_NODE_DATA}
          }}
        }}
      }}
    }}
    """
    __GRAPH_QL_REPO_CONTRIBUTED_QUERY_STR: str = f"""
    query ($login: String!, $num: Int!, $after: String, $field: RepositoryOrderField!) {{
      user(login: $login) {{
        repositoriesContributedTo(
          first: $num
          after: $after
          contributionTypes: [COMMIT]
          orderBy: {{ field: $field, direction: DESC }}
        ) {{
          {__GRAPH_QL_REPO_QUERY_PAGINATION}
          nodes {{
            {__GRAPH_QL_REPO_QUERY_NODE_DATA}
          }}
        }}
      }}
    }}
    """
    __GRAPH_QL_REPO_NAME_QUERY_STR: str = f"""
    query ($owner: String!, $name: String!) {{
      repository(owner: $owner, name: $name) {{
        {__GRAPH_QL_REPO_QUERY_NODE_DATA}
      }}
    }}
    """
    __GRAPH_QL_VERIFY_TOKEN_QUERY: str = """
    query { viewer { login } }
    """
    __GRAPH_QL_USER_DATA_QUERY: str = """
    query($login: String!) {
      user(login: $login) {
        login
        name
        databaseId
        createdAt
      }
    }
    """
    __GRAPH_QL_DEFAULT_TIME_OUT: int = 10
    __DEFAULT_FETCH_LIMIT: int = 100

    def __init__(
        self, api_token: str, username: str = None, fetch_limit: int = None
    ) -> None:
        self.__api_headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "Connection": "keep-alive",
            "User-Agent": "hf-pr-counter/1.0",
            "Authorization": f"Bearer {api_token}",
        }
        self.__fetch_limit: int = (
            fetch_limit if fetch_limit else self.__DEFAULT_FETCH_LIMIT
        )

        try:
            self.__gh_config_data: GitHubCredentialData = GitHubCredentialData(
                *self.__verify_user(username=username)
            )
        except AssertionError as err:
            raise GitHubGraphQlClientError(msg=f"API authorization error: {err}")

    def __raise_api_fetch_err(
        self, res: Response, exception: type[BaseException] = GitHubGraphQlClientError
    ) -> None:
        raise exception(
            f"{(res.json().get("errors") or {}).get("message")
            if res.json().get("error")
            else (
                res.json()["errors"][0].get("message")
                if isinstance(res.json().get("errors"), list) and res.json()["errors"]
                else (
                    res.json().get("message") 
                    if res.json().get("message") 
                    else "Bad credentials"
                )
            )}"
        )

    def __post_request(self, body_json: dict) -> dict[str, str | list[str]] | None:
        try:
            res: Response = post(
                self.__GRAPH_QL_URL,
                headers=self.__api_headers,
                json=body_json,
                timeout=self.__GRAPH_QL_DEFAULT_TIME_OUT,
            )
            if res.status_code == HTTPStatus.OK:
                return res.json()
            elif res.status_code == HTTPStatus.UNAUTHORIZED or not (
                (res.json().get("data") or {}).get("viewer") or {}
            ).get("login", None):
                self.__raise_api_fetch_err(res=res)
            else:
                self.__raise_api_fetch_err(res=res)
        except Exception as err:
            raise GitHubGraphQlClientError(msg=f"API request error: {err}")

    def __get_user_config(self, username: str) -> tuple[str, int, str]:
        res: dict[str, str | list[str]] = self.__post_request(
            body_json={
                "query": self.__GRAPH_QL_USER_DATA_QUERY,
                "variables": {"login": username},
            }
        )
        return (
            ((res.get("data") or {}).get("user") or {}).get("name", ""),
            ((res.get("data") or {}).get("user") or {}).get("databaseId", 0),
            ((res.get("data") or {}).get("user") or {}).get("createdAt", ""),
        )

    def __verify_user(self, username: str = None) -> tuple[str, str, int, str]:
        res: dict[str, str | list[str]] = self.__post_request(
            body_json={"query": self.__GRAPH_QL_VERIFY_TOKEN_QUERY}
        )
        res_username: str = (
            ((res.get("data") or {}).get("viewer") or {}).get("login", "").strip()
        )
        if not username:
            username = res_username
        return (username, *self.__get_user_config(username=username))

    def __process_repo_req(
        self, body_json: dict, repo_data_key: str, is_user_data: bool = True
    ) -> dict:
        res_data: dict = self.__post_request(body_json=body_json).get("data") or {}
        return (res_data.get("user") or {} if is_user_data else res_data).get(
            repo_data_key
        ) or {}

    def __paginate_fetch_repo_data(
        self, body_json: dict, repo_data_key: str, pinned_repo_urls: list
    ) -> list[dict[str, str | int | dict[str, str]]]:
        res_node_data: list[dict[str, str | int | dict[str, str]]] = []
        repo_urls: set[str] = set(pinned_repo_urls)
        after: str | None = None

        while True:
            repo_data: dict = self.__process_repo_req(
                body_json=(
                    body_json["variables"].update({"after": after}) or body_json
                ),
                repo_data_key=repo_data_key,
            )
            for node in repo_data.get("nodes", []):
                if not node:
                    continue
                url: str = node.get("url", "")
                if url in repo_urls:
                    continue
                repo_urls.add(url)
                res_node_data.append(node)

            if not repo_data.get("pageInfo", {}).get("hasNextPage"):
                break
            after = repo_data.get("pageInfo", {}).get("endCursor")

        return res_node_data

    @property
    def user_id(self) -> int | None:
        return self.__gh_config_data.user_id

    @property
    def user_name(self) -> str:
        return self.__gh_config_data.user_name

    @property
    def username(self) -> str:
        return self.__gh_config_data.username

    def fetch_pinned_repo_data(
        self, num_repos: int = None
    ) -> list[dict[str, str | int | dict[str, str]]]:
        pinned_repos: dict = self.__process_repo_req(
            body_json={
                "query": self.__GRAPH_QL_REPO_PIN_QUERY_STR,
                "variables": {
                    "login": self.__gh_config_data.username,
                    "num": num_repos if num_repos else self.__fetch_limit,
                },
            },
            repo_data_key="pinnedItems",
        )
        return [edge["node"] for edge in pinned_repos.get("edges", [])]

    def fetch_owned_or_contributed_to_repo_data(
        self,
        order_field: enums.RepositoryOrderFieldEnum = None,
        pinned_repo_urls: list[str] = None,
        is_contributed: bool = False,
    ) -> list[dict[str, str | int | dict[str, str]]]:
        return self.__paginate_fetch_repo_data(
            body_json={
                "query": (
                    self.__GRAPH_QL_REPO_CONTRIBUTED_QUERY_STR
                    if is_contributed
                    else self.__GRAPH_QL_REPO_OWN_QUERY_STR
                ),
                "variables": {
                    "login": self.__gh_config_data.username,
                    "num": self.__fetch_limit,
                    "field": (
                        order_field.name
                        if order_field
                        else enums.RepositoryOrderFieldEnum.STARGAZERS.name
                    ).upper(),
                },
            },
            repo_data_key=(
                "repositoriesContributedTo" if is_contributed else "repositories"
            ),
            pinned_repo_urls=pinned_repo_urls if pinned_repo_urls else [],
        )

    def fetch_single_repo_data(
        self,
        repo_owner: str = None,
        repo_name: str = None,
    ) -> dict[str, str | int | dict[str, str]]:
        return self.__process_repo_req(
            body_json={
                "query": self.__GRAPH_QL_REPO_NAME_QUERY_STR,
                "variables": {
                    "login": self.__gh_config_data.username,
                    "owner": repo_owner,
                    "name": repo_name,
                },
            },
            repo_data_key="repository",
            is_user_data=False,
        )
