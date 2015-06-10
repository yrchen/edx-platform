;(function (define) {
    'use strict';
    define(['backbone', 'underscore', 'common/js/components/views/paging', 'teams/js/views/topic_card'],
        function (Backbone, _, PagingView, TopicCardView) {
            var TeamsListView = Backbone.View.extend({
                tagName: 'div',
                className: 'topic-list',

                initialize: function() {
                    this.paging_topic_view = this.PagingTopicView(this.collection);
                },

                PagingTopicView: PagingView.extend({
                    renderPageItems: function () {
                        this.collection.each(function(topic) {
                            var topic_card_view = new TopicCardView({model: topic, el: $(".topic-list")});
                            topic_card_view.render();
                        });
                    }
                })
            });
            return TeamsListView;
}).call(this, define || RequireJS.define);
