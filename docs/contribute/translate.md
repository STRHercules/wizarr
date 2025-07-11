# Translate

Thanks for your interest in contributing to Wizarr!

### Weblate

We use Weblate to help translate Wizarr!&#x20;

{% embed url="https://hosted.weblate.org/engage/wizarr/" %}



### Testing Translations

After you have saved a translation, it will be pushed to the `master` branch directly. The `dev` Docker image will then be automatically compiled shortly thereafter.&#x20;

You can test translations locally without Docker by forcing a language when running the development server:

```bash
FORCE_LANGUAGE=en uv run flask run
```



