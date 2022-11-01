import os

from azure.identity import (
    AuthenticationRecord,
    ClientSecretCredential,
    DeviceCodeCredential,
    TokenCachePersistenceOptions,
)


def get_default_credential(name, scopes, **kwargs):
    """Retrieves default credentials.

    Parameters
    ----------
    name : str
        Name of the cache, used to isolate its data from other applications.
        Only applicable if the credential is cached on disk.
    scopes : list, of type str
        The scopes used to authenticate the credential.
        This argument is added as a default to the `get_token` method.
    kwargs : dict
        Keyword arguments passed to the credential constructors.
        If `client_secret` is present, the `ClientSecretCredential` is used. Otherwise,
        the `DeviceCodeCredential` is used.

    """
    if kwargs.get("client_secret") is not None:
        credential = ClientSecretCredential(**kwargs)
    else:
        allow_unencrypted_storage = (
            os.getenv("ALLOW_UNENCRYPTED_STORAGE", "false").lower() == "true"
        )
        cache_persistence_filepath = os.path.expanduser(
            os.path.join("~", ".authentication-records", name)
        )
        cache_persistence_options = TokenCachePersistenceOptions(
            name=name,
            allow_unencrypted_storage=allow_unencrypted_storage,
        )
        try:
            try:
                # Try to retrieve cached credentials
                with open(cache_persistence_filepath, "r") as f:
                    authentication_record = AuthenticationRecord.deserialize(f.read())
                credential = DeviceCodeCredential(
                    authentication_record=authentication_record,
                    cache_persistence_options=cache_persistence_options,
                )
            except FileNotFoundError:
                # Try to instantiate credentials with cache options
                credential = DeviceCodeCredential(
                    **kwargs,
                    cache_persistence_options=cache_persistence_options,
                )
                authentication_record = credential.authenticate(scopes=scopes)
                os.makedirs(os.path.dirname(cache_persistence_filepath), exist_ok=True)
                with open(cache_persistence_filepath, "w") as f:
                    f.write(authentication_record.serialize())
        except ValueError as e:
            # Linux 'headless' sessions do not support encryption
            if not str(e).startswith("Cache encryption is impossible"):
                raise
            credential = DeviceCodeCredential(**kwargs)
            # Prompt the user for a device code immediately
            credential.authenticate(scopes=scopes)

    # Overrides `get_token` to use `scopes` if no other arguments are passed
    credential.get_token = lambda *args, **kwargs: type(credential).get_token(
        credential, *(args or scopes), **kwargs
    )

    return credential


def remove_cached_credential(name):
    """Removes cached credential by name.

    Parameters
    ----------
    name : str
        Name of previously cached credential.

    """
    # This is where the session information is stored
    authentication_records_filepath = os.path.expanduser(
        os.path.join("~", ".authentication-records", name)
    )
    # This is where the actual credentials are stored
    identity_service_filepath = os.path.expanduser(
        os.path.join("~", ".IdentityService", name)
    )
    os.remove(authentication_records_filepath)
    os.remove(identity_service_filepath)
