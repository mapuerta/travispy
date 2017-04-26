from travispy import TravisPy
from travispy.entities import User
from travispy.errors import TravisError
import pytest
import time


@pytest.fixture(scope='module')
def travis(test_settings):
    token = test_settings.get('github_token', '')
    if not token.strip():
        pytest.skip('TRAVISPY_TEST_SETTINGS has no "github_token" value')

    try:
        result = TravisPy.github_auth(token)
    except TravisError:
        pytest.skip('Provided "github_token" value is invalid')

    return result


def wait_condition(expression, fail_msg, timeout=10):
    count = 0
    while expression():
        if count >= timeout:
            assert False, fail_msg
        time.sleep(1)
        count += 1


def test_account(travis, test_settings):
    expected = test_settings.get('account')
    if not expected:
        pytest.skip('TRAVISPY_TEST_SETTINGS has no "account" value')

    accounts = travis.accounts()
    assert len(accounts) == expected['count']

    account = travis.account(accounts[0].id)
    assert account.id == expected['id']
    assert account.name == expected['name']
    assert account.login == expected['login']
    assert account.type == expected['type']
    assert account.repos_count == expected['repos_count']
    assert hasattr(account, 'subscribed') == expected['subscribed']

    account = travis.account(123)
    assert account is None


def test_broadcast(travis):
    broadcasts = travis.broadcasts()
    assert isinstance(broadcasts, list)


def test_build(travis, test_settings, repo_slug):
    pytest.raises(RuntimeError, travis.builds)

    builds = travis.builds(slug=repo_slug)
    build = builds[0]

    wait_condition(
        lambda: not build.restart(),
        'Failed while restarting build',
    )

    wait_condition(
        lambda: not build.cancel(),
        'Failed while canceling build',
    )


def test_hook(travis, test_settings):
    expected = test_settings.get('hook')
    if not expected:
        pytest.skip('TRAVISPY_TEST_SETTINGS has no "hook" value')

    hooks = travis.hooks()
    assert len(hooks) == expected['count']

    hook = hooks[0]
    assert hook.name == expected['name']
    assert hook.description == expected['description']
    assert hook.owner_name == expected['owner_name']
    assert hook.active == expected['active']
    assert hook.private == expected['private']
    assert hook.admin == expected['admin']


def test_job(travis, repo_slug):
    pytest.raises(RuntimeError, travis.jobs)

    builds = travis.builds(slug=repo_slug)
    build = builds[0]

    jobs = travis.jobs(ids=build.job_ids)
    job = jobs[0]

    wait_condition(
        lambda: not job.restart(),
        'Failed while restarting job',
    )

    wait_condition(
        lambda: not job.cancel(),
        'Failed while canceling job',
    )


def test_repo(travis, test_settings, repo_slug):
    from travispy.entities import Build

    expected = test_settings.get('repo')
    if not expected:
        pytest.skip('TRAVISPY_TEST_SETTINGS has no "repo" value')

    repos = travis.repos()
    assert len(repos) == expected['public_count']

    repos = travis.repos(member='travispy')
    assert len(repos) == expected['member_count']

    repos = travis.repos(owner_name='travispy')
    assert len(repos) == expected['owner_count']

    repo = travis.repo(repo_slug)
    assert repo.slug == repo_slug
    assert repo.github_language == expected['github_language']
    assert repo.id == expected['id']
    assert repo.description == expected['description']
    assert repo.active == expected['active']

    assert hasattr(repo, 'last_build_id')
    assert hasattr(repo, 'last_build_number')
    assert hasattr(repo, 'last_build_state')
    assert hasattr(repo, 'last_build_duration')
    assert hasattr(repo, 'last_build_started_at')
    assert hasattr(repo, 'last_build_finished_at')
    assert hasattr(repo, 'state')

    last_build = repo.last_build
    assert isinstance(last_build, Build)
    assert last_build.repository_id == repo.id
    assert last_build == repo.last_build

    repo.last_build_id = -1
    with pytest.raises(TravisError) as exception_info:
        repo.last_build
    assert str(exception_info.value) == '[404] not found'


def test_repo_enable_disable(travis, repo_slug):
    repo = travis.repo(repo_slug)

    # check active so we try to return status to original state
    if repo.active:
        assert repo.disable()
        assert not(repo.active)
        assert repo.enable()
        assert repo.active
    else:
        assert repo.enable()
        assert repo.active
        assert repo.disable()
        assert not(repo.active)


def test_user(travis, test_settings):
    expected = test_settings.get('user')
    if not expected:
        pytest.skip('TRAVISPY_TEST_SETTINGS has no "user" value')

    user = travis.user()
    assert isinstance(user, User) is True

    # Accessing values using __getitem__
    assert user['login'] == expected['login']
    assert user['name'] == expected['name']

    # test sync
    assert user.sync()


def test_setting(travis, test_settings, repo_slug):
    expected = test_settings.get('settings')
    if not expected:
        pytest.skip('TRAVISPY_TEST_SETTINGS has no "settings" value')
    repo = travis.repo(repo_slug)
    setting = travis.settings(repo.id)
    setting.fingerprint = expected['fingerprint']
    setting.description = expected['description']
