/**
 * TECH LOG - Strict 4-Card Grid & 5-Page Block Numbered Pager Engine
 */
(function() {
  'use strict';

  var postPerPage = 4;   // 한 페이지당 정확히 글 4개만 노출
  var pageBlockSize = 5; // 한 번에 표시할 숫자 페이지 번호 개수 (5개 단위)
  var allPosts = [];
  var currentPage = 1;

  function enforceInitial4CardGrid() {
    var container = document.querySelector('#main-posts-grid, .posts-grid, .blog-posts, .tech-featured-grid');
    if (!container) return;

    var cards = Array.from(container.children).filter(function(child) {
      return child.classList.contains('post-card') || child.classList.contains('tech-post-card') || child.tagName === 'ARTICLE';
    });

    if (cards.length > postPerPage && allPosts.length === 0) {
      for (var i = postPerPage; i < cards.length; i++) {
        cards[i].style.display = 'none';
      }
    }
  }

  function formatBloggerDate(dateStr) {
    if (!dateStr) return '';
    try {
      var d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return (d.getMonth() + 1) + '월 ' + d.getDate() + ', ' + d.getFullYear();
    } catch(e) {
      return dateStr;
    }
  }

  function renderPage(page) {
    var container = document.querySelector('#main-posts-grid, .posts-grid, .blog-posts, .tech-featured-grid');
    if (!container) return;

    currentPage = page;
    var totalPages = Math.ceil(allPosts.length / postPerPage);
    if (page < 1) currentPage = 1;
    if (page > totalPages) currentPage = totalPages;

    var startIdx = (currentPage - 1) * postPerPage;
    var endIdx = startIdx + postPerPage;
    var pagePosts = allPosts.slice(startIdx, endIdx);

    container.innerHTML = '';
    pagePosts.forEach(function(post) {
      var article = document.createElement('article');
      article.className = 'post-card tech-post-card';
      
      var badgeCat = (post.labels && post.labels.length > 0) ? post.labels[0] : 'TECH';
      var tagsHtml = '';
      if (post.labels && post.labels.length > 0) {
        tagsHtml = '<div class="devlog-tags post-tags">';
        post.labels.slice(0, 4).forEach(function(lbl) {
          tagsHtml += '<a class="tech-tag" href="/search/label/' + encodeURIComponent(lbl) + '?max-results=4">' + lbl + '</a>';
        });
        tagsHtml += '</div>';
      }

      var formattedDate = formatBloggerDate(post.published);

      article.innerHTML = 
        '<div class="post-card-body tech-post-body">' +
          '<span class="post-category-badge tech-post-category">' + badgeCat + '</span>' +
          '<h2 class="post-card-title"><a href="' + post.url + '">' + post.title + '</a></h2>' +
          tagsHtml +
        '</div>' +
        '<div class="post-card-meta tech-post-meta">' +
          '<span>📅 ' + formattedDate + '</span>' +
        '</div>';
      
      container.appendChild(article);
    });

    render5BlockPagerControls(totalPages);

    window.scrollTo({
      top: container.offsetTop - 100,
      behavior: 'smooth'
    });
  }

  function render5BlockPagerControls(totalPages) {
    var pager = document.getElementById('blog-pager');
    if (!pager) return;

    if (totalPages <= 1) {
      pager.style.display = 'none';
      return;
    }

    pager.style.display = 'flex';

    var currentBlock = Math.ceil(currentPage / pageBlockSize);
    var startPage = (currentBlock - 1) * pageBlockSize + 1;
    var endPage = Math.min(totalPages, startPage + pageBlockSize - 1);

    var html = '<div class="tech-pagination-numbers" style="display:inline-flex;gap:0.5rem;align-items:center;">';

    if (startPage > 1) {
      var prevBlockTarget = startPage - 1;
      html += '<button class="page-btn prev-block-btn" data-page="' + prevBlockTarget + '">« 이전</button>';
    } else {
      html += '<button class="page-btn prev-block-btn disabled" style="opacity:0.4;cursor:not-allowed;" disabled>« 이전</button>';
    }

    for (var p = startPage; p <= endPage; p++) {
      var activeClass = p === currentPage ? ' active' : '';
      var activeStyle = p === currentPage ? ' style="background:var(--primary-color, #2563eb);color:#ffffff;font-weight:700;"' : '';
      html += '<button class="page-btn num-btn' + activeClass + '" data-page="' + p + '"' + activeStyle + '>' + p + '</button>';
    }

    if (endPage < totalPages) {
      var nextBlockTarget = endPage + 1;
      html += '<button class="page-btn next-block-btn" data-page="' + nextBlockTarget + '">다음 »</button>';
    } else {
      html += '<button class="page-btn next-block-btn disabled" style="opacity:0.4;cursor:not-allowed;" disabled>다음 »</button>';
    }

    html += '</div>';
    pager.innerHTML = html;

    var buttons = pager.querySelectorAll('.page-btn[data-page]');
    buttons.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var targetP = parseInt(btn.getAttribute('data-page'), 10);
        if (targetP && targetP !== currentPage) {
          renderPage(targetP);
        }
      });
    });
  }

  function getSearchFilterCriteria() {
    if (!window.location.search) return null;
    var urlParams = new URLSearchParams(window.location.search);
    var q = urlParams.get('q');
    if (!q) return null;

    q = decodeURIComponent(q).trim();
    if (!q) return null;

    var targetLabels = [];
    var keywords = [];

    var parts = q.split(/\s+OR\s+|\s+/i);
    parts.forEach(function(part) {
      part = part.trim();
      if (part.indexOf('label:') === 0) {
        var labelName = part.substring(6).replace(/^["']|["']$/g, '').trim();
        if (labelName) targetLabels.push(labelName.toLowerCase());
      } else if (part) {
        keywords.push(part.toLowerCase());
      }
    });

    return {
      labels: targetLabels,
      keywords: keywords,
      rawQuery: q
    };
  }

  window.initBloggerFeedPagination = function(json) {
    var entries = (json.feed && json.feed.entry) ? json.feed.entry : [];
    allPosts = [];
    var filterCriteria = getSearchFilterCriteria();

    entries.forEach(function(entry) {
      var title = entry.title ? entry.title.$t : '';
      var published = entry.published ? entry.published.$t : '';
      var url = '';
      if (entry.link) {
        for (var i = 0; i < entry.link.length; i++) {
          if (entry.link[i].rel === 'alternate') {
            url = entry.link[i].href;
            break;
          }
        }
      }
      var labels = [];
      if (entry.category) {
        entry.category.forEach(function(cat) {
          if (cat.term) labels.push(cat.term);
        });
      }

      var postObj = {
        title: title,
        published: published,
        url: url,
        labels: labels
      };

      if (filterCriteria) {
        var matches = false;

        if (filterCriteria.labels.length > 0) {
          var lowerPostLabels = labels.map(function(l) { return l.toLowerCase(); });
          for (var lIdx = 0; lIdx < filterCriteria.labels.length; lIdx++) {
            if (lowerPostLabels.indexOf(filterCriteria.labels[lIdx]) !== -1) {
              matches = true;
              break;
            }
          }
        }

        if (!matches && filterCriteria.keywords.length > 0) {
          var lowerTitle = title.toLowerCase();
          var lowerPostLabelsStr = labels.join(' ').toLowerCase();
          for (var kIdx = 0; kIdx < filterCriteria.keywords.length; kIdx++) {
            var kw = filterCriteria.keywords[kIdx];
            if (lowerTitle.indexOf(kw) !== -1 || lowerPostLabelsStr.indexOf(kw) !== -1) {
              matches = true;
              break;
            }
          }
        }

        if (matches) {
          allPosts.push(postObj);
        }
      } else {
        allPosts.push(postObj);
      }
    });

    if (allPosts.length > 0) {
      renderPage(1);
    } else if (filterCriteria) {
      var postsContainer = document.querySelector('.blog-posts') || document.querySelector('.main-content') || document.getElementById('main');
      if (postsContainer) {
        postsContainer.innerHTML = '<div style="text-align:center; padding: 4rem 1rem; color: #64748b; background: #ffffff; border-radius: 12px; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"><h3 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; color:#1e293b;">검색 결과가 없습니다</h3><p style="font-size: 0.95rem;">검색 쿼리: "' + filterCriteria.rawQuery + '"</p></div>';
      }
    }
  };

  document.addEventListener("DOMContentLoaded", function() {
    enforceInitial4CardGrid();
    setTimeout(enforceInitial4CardGrid, 300);
    setTimeout(enforceInitial4CardGrid, 1000);

    if (window.location.pathname.indexOf('/20') !== 0 || window.location.pathname.indexOf('.html') === -1) {
      var script = document.createElement('script');
      script.src = '/feeds/posts/summary?alt=json-in-script&max-results=150&callback=initBloggerFeedPagination';
      document.body.appendChild(script);
    }
  });

})();
