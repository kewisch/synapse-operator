<!-- markdownlint-disable -->

<a href="../src/synapse/api.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `api`
Helper module used to manage interactions with Synapse API. 

**Global Variables**
---------------
- **SYNAPSE_PORT**
- **SYNAPSE_URL**
- **ADD_USER_ROOM_URL**
- **CREATE_ROOM_URL**
- **DEACTIVATE_ACCOUNT_URL**
- **LIST_ROOMS_URL**
- **LIST_USERS_URL**
- **LOGIN_URL**
- **MJOLNIR_MANAGEMENT_ROOM**
- **MJOLNIR_MEMBERSHIP_ROOM**
- **REGISTER_URL**
- **SYNAPSE_VERSION_REGEX**
- **VERSION_URL**

---

<a href="../src/synapse/api.py#L96"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `register_user`

```python
register_user(
    registration_shared_secret: str,
    user: User,
    server: Optional[str] = None,
    admin_access_token: Optional[str] = None
) → str
```

Register user. 



**Args:**
 
 - <b>`registration_shared_secret`</b>:  secret to be used to register the user. 
 - <b>`user`</b>:  user to be registered. 
 - <b>`server`</b>:  to be used to create the user id. 
 - <b>`admin_access_token`</b>:  admin access token to get user's access token if it exists. 



**Raises:**
 
 - <b>`RegisterUserError`</b>:  if there was an error registering the user. 



**Returns:**
 Access token to be used by the user. 


---

<a href="../src/synapse/api.py#L213"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_version`

```python
get_version() → str
```

Get version. 

Expected API output: {  "server_version": "0.99.2rc1 (b=develop, abcdef123)",  "python_version": "3.7.8" } 

We're using retry here because after the config change, Synapse is restarted. 



**Returns:**
  The version returned by Synapse API. 



**Raises:**
 
 - <b>`GetVersionError`</b>:  if there was an error while reading version. 
 - <b>`VersionUnexpectedContentError`</b>:  if the version has unexpected content. 


---

<a href="../src/synapse/api.py#L245"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_access_token`

```python
get_access_token(user: User, server: str, admin_access_token: str) → str
```

Get an access token that can be used to authenticate as that user. 

This is a way to do actions on behalf of a user. 



**Args:**
 
 - <b>`user`</b>:  the user on behalf of whom you want to request the access token. 
 - <b>`server`</b>:  to be used to create the user id. User ID example: @user:server.com. 
 - <b>`admin_access_token`</b>:  a server admin access token to be used for the request. 



**Returns:**
 Access token. 



**Raises:**
 
 - <b>`GetAccessTokenError`</b>:  if there was an error while getting access token. 


---

<a href="../src/synapse/api.py#L274"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `override_rate_limit`

```python
override_rate_limit(
    user: User,
    admin_access_token: str,
    charm_state: CharmState
) → None
```

Override user's rate limit. 



**Args:**
 
 - <b>`user`</b>:  user to be used for requesting access token. 
 - <b>`admin_access_token`</b>:  server admin access token to be used. 
 - <b>`charm_state`</b>:  Instance of CharmState. 


---

<a href="../src/synapse/api.py#L292"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_room_id`

```python
get_room_id(room_name: str, admin_access_token: str) → Optional[str]
```

Get room id. 



**Args:**
 
 - <b>`room_name`</b>:  room name. 
 - <b>`admin_access_token`</b>:  server admin access token to be used. 



**Returns:**
 The room id. 



**Raises:**
 
 - <b>`GetRoomIDError`</b>:  if there was an error while getting room id. 


---

<a href="../src/synapse/api.py#L328"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `deactivate_user`

```python
deactivate_user(user: User, server: str, admin_access_token: str) → None
```

Deactivate user. 



**Args:**
 
 - <b>`user`</b>:  user to be deactivated. 
 - <b>`server`</b>:  to be used to create the user id. 
 - <b>`admin_access_token`</b>:  server admin access token to be used. 


---

<a href="../src/synapse/api.py#L350"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `create_management_room`

```python
create_management_room(admin_access_token: str) → str
```

Create the management room to be used by Mjolnir. 



**Args:**
 
 - <b>`admin_access_token`</b>:  server admin access token to be used. 



**Raises:**
 
 - <b>`GetRoomIDError`</b>:  if there was an error while getting room id. 



**Returns:**
 Room id. 


---

<a href="../src/synapse/api.py#L404"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `make_room_admin`

```python
make_room_admin(
    user: User,
    server: str,
    admin_access_token: str,
    room_id: str
) → None
```

Make user a room's admin. 



**Args:**
 
 - <b>`user`</b>:  user to add to the room as admin. 
 - <b>`server`</b>:  to be used to create the user id. 
 - <b>`admin_access_token`</b>:  server admin access token to be used for the request. 
 - <b>`room_id`</b>:  room id to add the user. 


---

<a href="../src/synapse/api.py#L43"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `APIError`
Exception raised when something fails while calling the API. 

Attrs:  msg (str): Explanation of the error. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L59"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `NetworkError`
Exception raised when requesting API fails due network issues. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L63"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `GetNonceError`
Exception raised when getting nonce fails. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L67"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `GetVersionError`
Exception raised when getting version fails. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L71"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `VersionUnexpectedContentError`
Exception raised when output of getting version is unexpected. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L75"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `GetRoomIDError`
Exception raised when getting room id fails. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L79"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `GetUserIDError`
Exception raised when getting user id fails. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L83"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `UserExistsError`
Exception raised when checking if user exists fails. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L87"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `GetAccessTokenError`
Exception raised when getting access token fails. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





---

<a href="../src/synapse/api.py#L91"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>class</kbd> `RegisterUserError`
Exception raised when registering user fails. 

<a href="../src/synapse/api.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the APIError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





