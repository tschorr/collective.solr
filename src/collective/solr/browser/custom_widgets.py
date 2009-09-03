from zope.app.form.browser import ObjectWidget, ListSequenceWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form import CustomWidgetFactory
from collective.solr.score import ScoreFactory

class HiddenReadonlyObjectWidget(ObjectWidget):
    """an object widget which hide all readonly attributes """
    
    template = ViewPageTemplateFile('hidden_readonly_object.pt')
    def __call__(self):
        return self.template()

solar_score_widget = CustomWidgetFactory(HiddenReadonlyObjectWidget, ScoreFactory)
solar_scores_widget = CustomWidgetFactory(ListSequenceWidget, solar_score_widget)