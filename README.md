# pybofh

*pybofh* is an interactive XMLRPC client for a `Cerebrum.modules.bofhd`
server. If you don't know what [Cerebrum][crb_about] is, you probably don't
want this.


## Install

We recommend that you use [virtualenv][virtualenv] to install *pybofh*.

```bash
python setup.py install
```


## Use

```bash
pybofh --help
python -m bofh --help
```


## Documentation

You'll have to build the *pybofh* documentation yourself (for now).

```bash
python setup.py build_sphinx
cd build/sphinx/html
python3 -m http.server
```
Then go to <http://localhost:8000/>.

For other documentation formats, see [docs/README.md](docs/README.md) and
[docs/Makefile](docs/Makefile).


## Module usage

```python
import bofh
from getpass import getuser, getpass

# Get a client by connecting to bofhd
url = 'https://example.org:8000'
cacert = '/path/to/ca.pem'
client = bofh.connect(url=url, cert=cacert)

# You'll need to authenticate to access restricted commands
client.login(getuser(), getpass())

# Call commands on the client object
try:
    # formatted output
    client.user.info('foo')

    # structured output
    client.run_command('user_info', 'foo')
finally:
    client.logout()
```

  [crb_about]: https://www.usit.uio.no/om/tjenestegrupper/cerebrum/
  [crb_src]: https://bitbucket.usit.uio.no/projects/CRB/repos/cerebrum/
  [virtualenv]: https://virtualenv.pypa.io/
