;(function (define) {
    'use strict';
    define(['backbone', 'js/components/card/views/card'],
        function (Backbone, CardView) {
            var TopicCardView = CardView.extend({
                action: function () {
                    console.log("Navigating to topic_id " + this.model.get('topic_id'));
                },

                render: function () {
                    this.$el.html(this.template({
                        name: this.model.get('name'),
                        description: this.model.get('description'),
                        action_text: 'View',
                        items: [this.model.get('team_count') + ' Teams'],
                        right_item: ''
                    }));
                    return this;
                }
            });

            return TopicCardView;
        });
}).call(this, define || RequireJS.define);