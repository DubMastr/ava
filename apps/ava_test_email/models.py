from django.db import models
from django.contrib.auth.models import User
from django.db.models import Model
from apps.ava_core.models import TimeStampedModel,ReferenceModel
from apps.ava_test.models import Test

class EmailTest(Test):
    emailtesttype = models.ForeignKey('EmailTestType', null=False)
    fromaddr = models.EmailField(null=False)
    subject = models.TextField(max_length=200,null=False)
    body = models.TextField(max_length=2000,null=False)
    messagetype = models.ForeignKey('EmailMessageType', null=False)


    def __unicode__(self):
        return self.name or u''


class EmailTestType (ReferenceModel):
    pass


class EmailMessageType (ReferenceModel):
    pass


class EmailTestTarget(TimeStampedModel):
    emailtest=models.ForeignKey('EmailTest', null=False)
    target = models.ForeignKey('ava_core_people.Identifier', null=False)
    token = models.CharField(max_length=100, null=False, unique=True)

    class Meta:
        unique_together = ("emailtest", "target", "token")

    def __unicode__(self):
        return self.target or u''

class EmailTemplate(Model):
    subject = models.TextField()
    message = models.TextField()

    def __unicode__(self):
        return self.subject or u''
