from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_bleach.models import BleachField


class Agreement(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name=_("Name"),
    )

    text = BleachField(
        verbose_name=_("Text"),
    )

    begin = models.DateField(
        verbose_name=_("Begin date"),
    )

    def __str__(self):
        return "{} ({})".format(self.name, self.begin)


class UserAgreement(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
    )

    agreed = models.DateTimeField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return "{} - {}".format(self.agreement, self.user)
